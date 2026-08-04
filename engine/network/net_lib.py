from core import *

class NetLib:

    @staticmethod
    def ListLocalIpAddresses():
        import socket
        ip_addresses: List[str] = []
        hostname = socket.gethostname()  # Get the local machine name
        local_ip = socket.gethostbyname(hostname)  # Get the local IP address
        ip_addresses.append(local_ip)

        # Get all IP addresses associated with the hostname
        for ip in socket.getaddrinfo(hostname, None):
            ip_addresses.append(ip[4][0])

        return sorted(set(ip_addresses))  # Use set to avoid duplicates

    @staticmethod
    def ExtractIpAndPort(input_string: str) -> Tuple[str, int]|None:
        # Updated regex pattern for matching IPv4 and IPv6 addresses with optional port
        import re
        ip_port_pattern = re.compile(r'''
            (?P<ip>
                (?:                             # Non-capturing group for IP
                    (?:\d{1,3}\.){3}\d{1,3}     # IPv4
                    |                           # OR
                    (?:                     # Start of IPv6 with brackets
                        \[?
                        (?:[0-9a-fA-F]{1,4}:    # Start of IPv6
                            (?:                     # Non-capturing group for IPv6
                                [0-9a-fA-F]{0,4}:   # 0-4 hex digits followed by a colon
                            ){0,7}                  # Up to 7 times
                            [0-9a-fA-F]{1,4}        # End with 1-4 hex digits
                        )
                        \]?
                    )                           # End of IPv6 with brackets
                )
            )
            (?::(?P<port>\d{1,5}))?            # Optional port (1-5 digits)
        ''', re.VERBOSE)
        match = ip_port_pattern.search(input_string)  # Use search instead of match
        if match:
            ip = match.group('ip')
            port_str = match.group('port')
            if port_str is not None:
                port = int(port_str)
                if 0 <= port <= 65535:  # Validate port range
                    return (ip, port)
        return None

    @staticmethod
    def IsPortAvailable(address: str, port: int) -> bool:
        import socket
        port_available = True

        if ':' in address:
            family = socket.AF_INET6
        else:
            family = socket.AF_INET

        s = socket.socket(family, socket.SOCK_STREAM)
        try:
            # Allow an immediately restarted server to bind while old connections
            # are still in TIME_WAIT. An active listener still keeps the port busy.
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((address, port))
        except OSError:
            port_available = False
        finally:
            s.close()
        return port_available
