import logging
import random
import socket
import struct
from typing import Any, Dict, List, Optional, Tuple

from twisted.internet import defer, protocol, reactor
from twisted.internet.defer import Deferred
from twisted.names import client, common, dns
from twisted.names.error import DNSQueryRefusedError, DNSServerError

from dns_proxy.cache import DNSCache
from dns_proxy.constants import (
    ALLOWED_QUERY_TYPES,
    CACHE_MAX_TTL,
    CACHE_MIN_TTL,
    CACHE_NEGATIVE_TTL,
    CNAME_DEFAULT_TTL,
    DNS_DEFAULT_PORT,
    DNS_QUERY_TIMEOUT,
    DNS_UDP_MAX_SIZE,
    LOG_QUERY_DETAILS,
    MAX_CNAME_RECURSION_DEPTH,
)

logger = logging.getLogger(__name__)


class DNSMessage:
    """DNS Message wrapper for easier manipulation"""

    def __init__(self, message: dns.Message):
        self.message = message
        self.answers = list(message.answers)
        self.authority = list(message.authority)
        self.additional = list(message.additional)

    def get_cname_records(self) -> List[dns.RRHeader]:
        """Get CNAME records from answers"""
        return [rr for rr in self.answers if rr.type == dns.CNAME]

    def get_a_records(self) -> List[dns.RRHeader]:
        """Get A records from answers"""
        return [rr for rr in self.answers if rr.type == dns.A]

    def remove_aaaa_records(self):
        """Remove AAAA records from all sections"""
        self.answers = [rr for rr in self.answers if rr.type != dns.AAAA]
        self.authority = [rr for rr in self.authority if rr.type != dns.AAAA]
        self.additional = [rr for rr in self.additional if rr.type != dns.AAAA]

    def to_message(self) -> dns.Message:
        """Convert back to dns.Message"""
        self.message.answers = self.answers
        self.message.authority = self.authority
        self.message.additional = self.additional
        return self.message


class CNAMEFlattener:
    """CNAME flattening resolver"""

    def __init__(
        self,
        upstream_resolver,
        max_recursion: int = MAX_CNAME_RECURSION_DEPTH,
        cache: DNSCache = None,
    ):
        self.upstream_resolver = upstream_resolver
        self.max_recursion = max_recursion
        self.cache = cache or DNSCache()

    @defer.inlineCallbacks
    def resolve_cname_chain(self, name: str, recursion_count: int = 0) -> List[str]:
        """Resolve CNAME chain to final A record names"""
        if recursion_count >= self.max_recursion:
            logger.warning(f"Max CNAME recursion reached for {name}")
            defer.returnValue([])

        # Check cache first - include class for proper caching
        cache_key = f"cname:{name}:IN"  # CNAMEs are typically IN class
        cached_result = self.cache.get(cache_key)
        if cached_result:
            defer.returnValue(cached_result)

        try:
            # Query for CNAME
            result = yield self.upstream_resolver.lookupCanonicalName(name)
            if result and result[0]:
                cname_record = result[0][0]
                target = str(cname_record.name)
                logger.debug(f"CNAME: {name} -> {target}")

                # Recursively resolve the target
                chain = yield self.resolve_cname_chain(target, recursion_count + 1)
                final_chain = [target] + chain

                # Cache the result
                ttl = getattr(cname_record, "ttl", CNAME_DEFAULT_TTL)
                self.cache.set(cache_key, final_chain, ttl=min(CACHE_MAX_TTL, ttl))
                defer.returnValue(final_chain)
            else:
                defer.returnValue([])

        except Exception as e:
            logger.debug(f"No CNAME found for {name}: {e}")
            defer.returnValue([])

    @defer.inlineCallbacks
    def flatten_cnames(self, dns_msg: DNSMessage, original_query_name: str) -> DNSMessage:
        """Flatten CNAME records to A records"""
        cname_records = dns_msg.get_cname_records()

        if not cname_records:
            defer.returnValue(dns_msg)

        logger.debug(f"Flattening {len(cname_records)} CNAME records for {original_query_name}")

        # Get all A records that should replace CNAMEs
        all_a_records = []

        for cname_rr in cname_records:
            target_name = str(cname_rr.payload.name)
            logger.debug(f"Resolving CNAME target: {target_name}")

            try:
                # Resolve target to A records
                a_result = yield self.upstream_resolver.lookupAddress(target_name)
                if a_result and a_result[0]:
                    logger.debug(f"Found {len(a_result[0])} A records for {target_name}")
                    for a_rr in a_result[0]:
                        # Create new A record with original query name
                        new_a_record = dns.RRHeader(
                            name=original_query_name,
                            type=dns.A,
                            cls=dns.IN,
                            ttl=min(cname_rr.ttl, a_rr.ttl),
                            payload=a_rr.payload,
                        )
                        all_a_records.append(new_a_record)
                        logger.debug(
                            f"Created A record: {original_query_name} -> {a_rr.payload.dottedQuad()}"
                        )
                else:
                    logger.warning(f"No A records found for CNAME target {target_name}")

            except Exception as e:
                logger.warning(f"Failed to resolve CNAME target {target_name}: {e}")

        if all_a_records:
            # Replace CNAME records with A records
            dns_msg.answers = [rr for rr in dns_msg.answers if rr.type != dns.CNAME]
            dns_msg.answers.extend(all_a_records)
            logger.info(
                f"Flattened CNAMEs for {original_query_name}: {len(all_a_records)} A records"
            )
        else:
            logger.warning(f"No A records found after flattening CNAMEs for {original_query_name}")

        # Remove AAAA records as requested
        aaaa_count = len([rr for rr in dns_msg.answers if rr.type == dns.AAAA])
        dns_msg.remove_aaaa_records()
        if aaaa_count > 0:
            logger.debug(f"Removed {aaaa_count} AAAA records for {original_query_name}")

        defer.returnValue(dns_msg)


class DNSProxyResolver:
    """Main DNS resolver with CNAME flattening"""

    def __init__(
        self,
        upstream_server: str,
        upstream_port: int = DNS_DEFAULT_PORT,
        max_recursion: int = MAX_CNAME_RECURSION_DEPTH,
        cache: DNSCache = None,
        remove_aaaa: bool = True,
    ):
        self.upstream_server = upstream_server
        self.upstream_port = upstream_port
        self.cache = cache or DNSCache()
        self.remove_aaaa = remove_aaaa

        # Create upstream resolver
        self.upstream_resolver = client.Resolver(
            servers=[(upstream_server, upstream_port)], timeout=(DNS_QUERY_TIMEOUT,)
        )

        # Initialize CNAME flattener
        self.cname_flattener = CNAMEFlattener(self.upstream_resolver, max_recursion, self.cache)

    @defer.inlineCallbacks
    def resolve_query(self, query: dns.Query) -> dns.Message:
        """Resolve DNS query with CNAME flattening"""
        query_name = str(query.name)
        query_type = query.type
        query_class = query.cls

        # Create cache key - FIXED: Include query class to prevent cache collisions
        cache_key = f"{query_name}:{query_type}:{query_class}"

        # Check cache first
        cached_response = self.cache.get(cache_key)
        if cached_response:
            logger.debug(f"Cache hit for {query_name}")
            defer.returnValue(cached_response)

        try:
            # Forward query to upstream - returns (answers, authority, additional)
            result = yield self.upstream_resolver.query(query)
            answers, authority, additional = result

            if answers:
                # Create a proper DNS message from the tuple result
                response = dns.Message()
                response.answers = list(answers)
                response.authority = list(authority)
                response.additional = list(additional)

                # Debug: Log what we got from upstream
                logger.debug(f"Upstream response for {query_name}:")
                logger.debug(f"  Answers: {len(response.answers)} records")
                for i, rr in enumerate(response.answers):
                    try:
                        if rr.type == dns.CNAME:
                            target = str(rr.payload.name)
                            logger.debug(f"    [{i}] CNAME: {rr.name} -> {target} (TTL: {rr.ttl})")
                        elif rr.type == dns.A:
                            ip = rr.payload.dottedQuad()
                            logger.debug(f"    [{i}] A: {rr.name} -> {ip} (TTL: {rr.ttl})")
                        elif rr.type == dns.AAAA:
                            logger.debug(
                                f"    [{i}] AAAA: {rr.name} -> {rr.payload} (TTL: {rr.ttl})"
                            )
                        else:
                            logger.debug(
                                f"    [{i}] {dns.QUERY_TYPES.get(rr.type, rr.type)}: {rr.name} -> {rr.payload} (TTL: {rr.ttl})"
                            )
                    except Exception as e:
                        logger.debug(
                            f"    [{i}] {dns.QUERY_TYPES.get(rr.type, rr.type)}: {rr.name} (debug error: {e})"
                        )

                logger.debug(f"  Authority: {len(response.authority)} records")
                logger.debug(f"  Additional: {len(response.additional)} records")

                # For A record queries, do CNAME flattening
                if query_type == dns.A or query_type == dns.AAAA:
                    # Check if we have any CNAME records in ANY section
                    cname_in_answers = [rr for rr in response.answers if rr.type == dns.CNAME]
                    cname_in_authority = [rr for rr in response.authority if rr.type == dns.CNAME]
                    cname_in_additional = [rr for rr in response.additional if rr.type == dns.CNAME]

                    total_cnames = (
                        len(cname_in_answers) + len(cname_in_authority) + len(cname_in_additional)
                    )

                    if total_cnames > 0:
                        logger.debug(
                            f"Found CNAMEs: {len(cname_in_answers)} in answers, {len(cname_in_authority)} in authority, {len(cname_in_additional)} in additional"
                        )

                        # Find A records that are final results of the CNAME chain
                        a_records_from_chain = [rr for rr in response.answers if rr.type == dns.A]
                        aaaa_records_from_chain = [
                            rr for rr in response.answers if rr.type == dns.AAAA
                        ]

                        if a_records_from_chain or aaaa_records_from_chain:
                            # Create flattened A records pointing to original query name
                            flattened_records = []
                            for a_rr in a_records_from_chain:
                                # ✅ SAFETY CHECK: Skip if not actually an A record
                                if a_rr.type != dns.A:
                                    logger.debug(f"Skipping non-A record: {a_rr.type}")
                                    continue
                                new_a_record = dns.RRHeader(
                                    name=query_name,
                                    type=dns.A,
                                    cls=dns.IN,
                                    ttl=a_rr.ttl,
                                    payload=a_rr.payload,
                                )
                                flattened_records.append(new_a_record)
                                logger.debug(
                                    f"Flattened A: {query_name} -> {a_rr.payload.dottedQuad()}"
                                )

                            # ✅ Process AAAA records (IPv6) if not removing them
                            if not self.remove_aaaa:
                                for aaaa_rr in aaaa_records_from_chain:
                                    new_aaaa_record = dns.RRHeader(
                                        name=query_name,
                                        type=dns.AAAA,  # ✅ AAAA type with AAAA payload
                                        cls=dns.IN,
                                        ttl=aaaa_rr.ttl,
                                        payload=aaaa_rr.payload,
                                    )
                                    flattened_records.append(new_aaaa_record)
                                    logger.debug(
                                        f"Flattened AAAA: {query_name} -> {aaaa_rr.payload}"
                                    )

                            # Build new response: start with flattened A records
                            new_answers = flattened_records[:]

                            # Replace response with flattened records (A + optionally AAAA)
                            response.answers = new_answers
                            response.authority = []  # Clear authority section completely
                            response.additional = []  # Clear additional section completely

                            logger.info(
                                f"CNAME flattening: {query_name} -> {len(flattened_records)} A records, removed {total_cnames} CNAMEs"
                            )
                        else:
                            logger.warning(f"Found CNAMEs but no A records for {query_name}")
                            # Still remove all CNAMEs even if no A records
                            response.answers = []
                            response.authority = []
                            response.additional = []
                    else:
                        # No CNAMEs, conditionally remove AAAA records from all sections
                        if self.remove_aaaa:
                            logger.debug(
                                f"No CNAMEs found for {query_name}, removing AAAA records only"
                            )
                            response.answers = [
                                rr for rr in response.answers if rr.type != dns.AAAA
                            ]
                            response.authority = [
                                rr for rr in response.authority if rr.type != dns.AAAA
                            ]
                            response.additional = [
                                rr for rr in response.additional if rr.type != dns.AAAA
                            ]
                        else:
                            logger.debug(f"No CNAMEs found for {query_name}, keeping IPv6 records")

                else:
                    # For non-A queries, conditionally remove AAAA and CNAME records from all sections
                    logger.debug(f"Non-A query for {query_name}")

                    # Always remove CNAMEs for non-A queries (they don't make sense)
                    cname_count = (
                        len([rr for rr in response.answers if rr.type == dns.CNAME])
                        + len([rr for rr in response.authority if rr.type == dns.CNAME])
                        + len([rr for rr in response.additional if rr.type == dns.CNAME])
                    )

                    response.answers = [rr for rr in response.answers if rr.type != dns.CNAME]
                    response.authority = [rr for rr in response.authority if rr.type != dns.CNAME]
                    response.additional = [rr for rr in response.additional if rr.type != dns.CNAME]

                    # Conditionally remove AAAA records
                    if self.remove_aaaa:
                        aaaa_count = (
                            len([rr for rr in response.answers if rr.type == dns.AAAA])
                            + len([rr for rr in response.authority if rr.type == dns.AAAA])
                            + len([rr for rr in response.additional if rr.type == dns.AAAA])
                        )

                        response.answers = [rr for rr in response.answers if rr.type != dns.AAAA]
                        response.authority = [
                            rr for rr in response.authority if rr.type != dns.AAAA
                        ]
                        response.additional = [
                            rr for rr in response.additional if rr.type != dns.AAAA
                        ]

                        if aaaa_count > 0:
                            logger.debug(
                                f"Removed {aaaa_count} AAAA records from non-A query (IPv6 removal enabled)"
                            )
                    else:
                        logger.debug("IPv6 removal disabled - keeping AAAA records for non-A query")

                # Final debug: Log what we're returning
                logger.debug(f"Final response for {query_name}:")
                logger.debug(f"  Answers: {len(response.answers)} records")
                logger.debug(f"  Authority: {len(response.authority)} records")
                logger.debug(f"  Additional: {len(response.additional)} records")

                # Cache the result - respect DNS TTLs up to configured maximum
                if response.answers:
                    min_ttl = min([rr.ttl for rr in response.answers])
                    # Cap at configured maximum but respect shorter TTLs
                    cache_ttl = min(min_ttl, CACHE_MAX_TTL)
                else:
                    cache_ttl = CACHE_NEGATIVE_TTL  # Use negative TTL for empty responses

                self.cache.set(cache_key, response, ttl=cache_ttl)

                defer.returnValue(response)
            else:
                # No answers, create empty response
                response = dns.Message()
                response.answers = []
                response.authority = list(authority)
                response.additional = list(additional)

                # Conditionally remove AAAA and CNAME from authority/additional even in empty responses
                response.authority = [rr for rr in response.authority if rr.type != dns.CNAME]
                response.additional = [rr for rr in response.additional if rr.type != dns.CNAME]

                if self.remove_aaaa:
                    response.authority = [rr for rr in response.authority if rr.type != dns.AAAA]
                    response.additional = [rr for rr in response.additional if rr.type != dns.AAAA]

                # Cache negative response with appropriate TTL
                self.cache.set(cache_key, response, ttl=CACHE_NEGATIVE_TTL)
                defer.returnValue(response)

        except Exception as e:
            logger.error(f"Failed to resolve {query_name}: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            # Return SERVFAIL
            error_response = dns.Message()
            error_response.rCode = dns.ESERVER
            defer.returnValue(error_response)


class DNSProxyProtocol(protocol.DatagramProtocol):
    """UDP DNS proxy protocol"""

    def __init__(self, resolver: DNSProxyResolver):
        self.resolver = resolver
        self.pending_queries: Dict[int, Tuple[str, int]] = {}

    def datagramReceived(self, data: bytes, addr: Tuple[str, int]):
        """Handle incoming DNS query"""
        try:
            # Parse DNS message
            message = dns.Message()
            message.fromStr(data)

            if not message.queries:
                logger.warning(f"Received DNS message with no queries from {addr}")
                return

            query = message.queries[0]
            query_id = message.id

            logger.debug(
                f"UDP Query from {addr}: {query.name} ({dns.QUERY_TYPES.get(query.type, query.type)})"
            )

            # Store client info for response
            self.pending_queries[query_id] = addr

            # Resolve query
            d = self.resolver.resolve_query(query)
            d.addCallback(self._send_response, query_id, message)
            d.addErrback(self._handle_error, query_id, message, addr)

        except Exception as e:
            logger.error(f"Error parsing UDP DNS query from {addr}: {e}")

    def _send_response(self, response: dns.Message, query_id: int, original_message: dns.Message):
        """Send DNS response back to client"""
        if query_id not in self.pending_queries:
            return

        addr = self.pending_queries.pop(query_id)

        # Set response fields
        response.id = query_id
        response.answer = True
        response.queries = original_message.queries

        try:
            response_data = response.toStr()

            # Check if response is too large for UDP
            if len(response_data) > DNS_UDP_MAX_SIZE:
                logger.debug(f"Response too large for UDP ({len(response_data)} bytes), truncating")
                # Set truncated flag
                response.trunc = True
                # Try to fit in UDP max size by removing additional records
                while len(response_data) > DNS_UDP_MAX_SIZE and response.additional:
                    response.additional.pop()
                    response_data = response.toStr()

            self.transport.write(response_data, addr)
            logger.debug(f"Sent UDP response to {addr} ({len(response_data)} bytes)")
        except Exception as e:
            logger.error(f"Failed to send UDP response to {addr}: {e}")

    def _handle_error(
        self, failure, query_id: int, original_message: dns.Message, addr: Tuple[str, int]
    ):
        """Handle query resolution error"""
        logger.error(f"UDP query resolution failed for {addr}: {failure}")

        if query_id in self.pending_queries:
            self.pending_queries.pop(query_id)

        # Send SERVFAIL response
        error_response = dns.Message()
        error_response.id = query_id
        error_response.answer = True
        error_response.rCode = dns.ESERVER
        error_response.queries = original_message.queries

        try:
            response_data = error_response.toStr()
            self.transport.write(response_data, addr)
        except Exception as e:
            logger.error(f"Failed to send UDP error response to {addr}: {e}")


class DNSTCPProtocol(protocol.Protocol):
    """TCP DNS proxy protocol for large responses"""

    def __init__(self, resolver: DNSProxyResolver):
        self.resolver = resolver
        self.buffer = b""

    def connectionMade(self):
        """Called when TCP connection is established"""
        self.peer = self.transport.getPeer()
        logger.debug(f"TCP connection from {self.peer.host}:{self.peer.port}")

    def dataReceived(self, data: bytes):
        """Handle incoming TCP DNS data"""
        self.buffer += data

        # DNS over TCP has 2-byte length prefix
        while len(self.buffer) >= 2:
            msg_length = struct.unpack("!H", self.buffer[:2])[0]

            if len(self.buffer) >= 2 + msg_length:
                # We have a complete message
                dns_data = self.buffer[2 : 2 + msg_length]
                self.buffer = self.buffer[2 + msg_length :]

                # Process the DNS message
                self._process_dns_message(dns_data)
            else:
                # Wait for more data
                break

    def _process_dns_message(self, dns_data: bytes):
        """Process a complete DNS message"""
        try:
            # Parse DNS message
            message = dns.Message()
            message.fromStr(dns_data)

            if not message.queries:
                logger.warning(f"Received TCP DNS message with no queries from {self.peer.host}")
                self.transport.loseConnection()
                return

            query = message.queries[0]
            query_id = message.id

            logger.debug(
                f"TCP Query from {self.peer.host}: {query.name} ({dns.QUERY_TYPES.get(query.type, query.type)})"
            )

            # Resolve query
            d = self.resolver.resolve_query(query)
            d.addCallback(self._send_tcp_response, query_id, message)
            d.addErrback(self._handle_tcp_error, query_id, message)

        except Exception as e:
            logger.error(f"Error parsing TCP DNS query from {self.peer.host}: {e}")
            self.transport.loseConnection()

    def _send_tcp_response(
        self, response: dns.Message, query_id: int, original_message: dns.Message
    ):
        """Send DNS response back over TCP"""
        try:
            # Set response fields
            response.id = query_id
            response.answer = True
            response.queries = original_message.queries

            response_data = response.toStr()

            # TCP DNS messages are prefixed with 2-byte length
            length_prefix = struct.pack("!H", len(response_data))
            full_response = length_prefix + response_data

            self.transport.write(full_response)
            logger.debug(f"Sent TCP response to {self.peer.host} ({len(response_data)} bytes)")

            # Close the connection after sending response
            self.transport.loseConnection()

        except Exception as e:
            logger.error(f"Failed to send TCP response to {self.peer.host}: {e}")
            self.transport.loseConnection()

    def _handle_tcp_error(self, failure, query_id: int, original_message: dns.Message):
        """Handle TCP query resolution error"""
        logger.error(f"TCP query resolution failed for {self.peer.host}: {failure}")

        try:
            # Send SERVFAIL response
            error_response = dns.Message()
            error_response.id = query_id
            error_response.answer = True
            error_response.rCode = dns.ESERVER
            error_response.queries = original_message.queries

            response_data = error_response.toStr()
            length_prefix = struct.pack("!H", len(response_data))
            full_response = length_prefix + response_data

            self.transport.write(full_response)
        except Exception as e:
            logger.error(f"Failed to send TCP error response to {self.peer.host}: {e}")
        finally:
            self.transport.loseConnection()


class DNSTCPFactory(protocol.Factory):
    """Factory for creating TCP DNS protocol instances"""

    def __init__(self, resolver: DNSProxyResolver):
        self.resolver = resolver

    def buildProtocol(self, addr):
        """Build a new TCP protocol instance"""
        return DNSTCPProtocol(self.resolver)
