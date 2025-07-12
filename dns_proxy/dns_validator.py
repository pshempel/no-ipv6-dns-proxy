# dns_proxy/dns_validator.py
# Version: 1.0.0
# DNS request/response validation for security

"""
DNS Validator Module

Provides security validation for DNS requests and responses to prevent:
- Buffer overflow attacks
- DNS amplification attacks
- Malformed packet attacks
- Resource exhaustion
"""

import logging

from twisted.names import dns

from dns_proxy.constants import (
    ALLOWED_QUERY_TYPES,
    DNS_UDP_MAX_SIZE,
    MAX_DNS_ANSWERS,
    MAX_DNS_LABEL_LENGTH,
    MAX_DNS_NAME_LENGTH,
    MAX_DNS_PACKET_SIZE,
    MAX_DNS_QUESTIONS,
    MIN_DNS_PACKET_SIZE,
)

logger = logging.getLogger(__name__)


class DNSValidationError(Exception):
    """DNS validation error"""

    pass


class DNSValidator:
    """Validates DNS requests and responses for security"""

    @staticmethod
    def validate_packet_size(data: bytes, is_tcp: bool = False) -> None:
        """
        Validate DNS packet size

        Args:
            data: Raw DNS packet data
            is_tcp: Whether this is a TCP packet

        Raises:
            DNSValidationError: If packet size is invalid
        """
        packet_size = len(data)

        # Check minimum size
        if packet_size < MIN_DNS_PACKET_SIZE:
            raise DNSValidationError(
                f"DNS packet too small: {packet_size} bytes (minimum {MIN_DNS_PACKET_SIZE})"
            )

        # Check maximum size
        max_size = MAX_DNS_PACKET_SIZE if is_tcp else DNS_UDP_MAX_SIZE
        if packet_size > max_size:
            raise DNSValidationError(
                f"DNS packet too large: {packet_size} bytes (maximum {max_size})"
            )

    @staticmethod
    def validate_dns_name(name: str) -> None:
        """
        Validate DNS name format

        Args:
            name: DNS name to validate

        Raises:
            DNSValidationError: If name is invalid
        """
        # Check total length
        if len(name) > MAX_DNS_NAME_LENGTH:
            raise DNSValidationError(
                f"DNS name too long: {len(name)} characters (maximum {MAX_DNS_NAME_LENGTH})"
            )

        # Check individual labels
        labels = name.split(".")
        for label in labels:
            if label and len(label) > MAX_DNS_LABEL_LENGTH:
                raise DNSValidationError(
                    f"DNS label too long: '{label}' is {len(label)} characters "
                    f"(maximum {MAX_DNS_LABEL_LENGTH})"
                )

            # Check for valid characters (alphanumeric and hyphen)
            if label and not all(c.isalnum() or c == "-" for c in label):
                raise DNSValidationError(f"Invalid characters in DNS label: '{label}'")

            # Labels can't start or end with hyphen
            if label and (label.startswith("-") or label.endswith("-")):
                raise DNSValidationError(f"DNS label cannot start or end with hyphen: '{label}'")

    @staticmethod
    def validate_message(message: dns.Message) -> None:
        """
        Validate parsed DNS message

        Args:
            message: Parsed DNS message

        Raises:
            DNSValidationError: If message is invalid
        """
        # Check number of questions
        queries = message.queries if message.queries else []
        if len(queries) > MAX_DNS_QUESTIONS:
            raise DNSValidationError(
                f"Too many questions in DNS query: {len(queries)} (maximum {MAX_DNS_QUESTIONS})"
            )

        # Validate each query
        for query in queries:
            # Validate query name
            try:
                DNSValidator.validate_dns_name(str(query.name))
            except DNSValidationError as e:
                raise DNSValidationError(f"Invalid query name: {e}")

            # Check query type
            if query.type not in ALLOWED_QUERY_TYPES:
                raise DNSValidationError(f"Unsupported query type: {query.type} for {query.name}")

        # If it's a response, check answer count
        if hasattr(message, "answer") and message.answer:
            answers = message.answers if message.answers else []
            authority = message.authority if message.authority else []
            additional = message.additional if message.additional else []
            total_records = len(answers) + len(authority) + len(additional)
            if total_records > MAX_DNS_ANSWERS:
                raise DNSValidationError(
                    f"Too many records in DNS response: {total_records} (maximum {MAX_DNS_ANSWERS})"
                )

    @staticmethod
    def validate_request(data: bytes, is_tcp: bool = False) -> dns.Message:
        """
        Validate incoming DNS request

        Args:
            data: Raw DNS request data
            is_tcp: Whether this is a TCP request

        Returns:
            Parsed and validated DNS message

        Raises:
            DNSValidationError: If request is invalid
        """
        # Validate packet size
        DNSValidator.validate_packet_size(data, is_tcp)

        # Try to parse the message
        try:
            message = dns.Message()
            message.fromStr(data)
        except Exception as e:
            raise DNSValidationError(f"Failed to parse DNS message: {e}")

        # Validate the parsed message
        DNSValidator.validate_message(message)

        # Additional checks for requests
        if not message.queries:
            raise DNSValidationError("DNS request has no queries")

        return message

    @staticmethod
    def validate_response(data: bytes, is_tcp: bool = False) -> dns.Message:
        """
        Validate DNS response

        Args:
            data: Raw DNS response data
            is_tcp: Whether this is a TCP response

        Returns:
            Parsed and validated DNS message

        Raises:
            DNSValidationError: If response is invalid
        """
        # Validate packet size
        DNSValidator.validate_packet_size(data, is_tcp)

        # Try to parse the message
        try:
            message = dns.Message()
            message.fromStr(data)
        except Exception as e:
            raise DNSValidationError(f"Failed to parse DNS response: {e}")

        # Validate the parsed message
        DNSValidator.validate_message(message)

        return message

    @staticmethod
    def create_error_response(
        query_id: int, query: dns.Query, error_code: int = dns.EFORMAT
    ) -> dns.Message:
        """
        Create an error response for invalid requests

        Args:
            query_id: Original query ID
            query: Original query (if available)
            error_code: DNS error code to return

        Returns:
            DNS error response message
        """
        error_response = dns.Message()
        error_response.id = query_id
        error_response.answer = True
        error_response.rCode = error_code

        if query:
            error_response.queries = [query]

        return error_response
