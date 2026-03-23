import sys
import logging
import argparse
from igscli import connect
from zeroconf import ServiceBrowser, Zeroconf

logging.basicConfig(
    stream = sys.stdout,
    level = logging.DEBUG,
    format = '[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger('__main__')

class MyListener:
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        # name looks like "IGS03E-v3.1.0 [mac]._ble-gw._tcp.local."
        # info.name looks like "IGS03E-v3.1.0" or similar
        if 'IGS03E' in info.name:
            ip = info.parsed_addresses()[0]
            logger.info('Found %s at %s' % (info.name, ip))
            
            # version detection
            protocol = 'ssh' # Default fallback
            try:
                # find the version part "-vX.Y.Z"
                import re
                match = re.search(r'-v(\d+)\.', info.name)
                if match:
                    version = int(match.group(1))
                    if version >= 3:
                        protocol = 'ssh'
                    else:
                        protocol = 'telnet'
                    logger.info(f"Detected version v{version}, using {protocol}")
            except Exception as e:
                logger.warning(f"Could not parse version from {info.name}, using fallback {protocol}: {e}")

            try:
                client = connect(ip, self.username, self.password, protocol=protocol)
                # configurate MQTT BULKMODE (example)
                value = client.get('MQTT BULKMODE')
                logging.info('Get MQTT BULKMODE = %s' % value)
                if value != '1':
                    logging.info('Set MQTT BULKMODE = 1')
                    client.exec('MQTT BULKMODE', 1)
                # add more configurate
                # done
                client.close()
            except Exception as e:
                logger.error(f"Failed to configure device at {ip}: {e}")

    def update_service(self, zeroconf, type, name):
        pass

    def remove_service(self, zeroconf, type, name):
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='iGS03E Auto Configuration Tool (via mDNS)')
    parser.add_argument('--username', default='admin', help='Username (default: admin)')
    parser.add_argument('--password', default='admin', help='Password (default: admin)')
    args = parser.parse_args()

    logger.info("Starting mDNS discovery. This will apply settings to ALL found IGS03E devices.")

    zeroconf = Zeroconf()
    listener = MyListener(username=args.username, password=args.password)
    browser = ServiceBrowser(zeroconf, "_ble-gw._tcp.local.", listener)
    try:
        input("Press enter to exit...\n\n")
    finally:
        zeroconf.close()
