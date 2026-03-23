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
    def __init__(self, username, password, protocol='ssh'):
        self.username = username
        self.password = password
        self.protocol = protocol

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if 'IGS03E' in info.name:
            ip = info.parsed_addresses()[0]
            logger.info('Found %s at %s' % (name, ip))
            try:
                client = connect(ip, self.username, self.password, protocol=self.protocol)
                # configurate HTTP CN_CHECK (example)
                value = client.get('HTTP CN_CHECK')
                logging.info('Get HTTP CN_CHECK = %s' % value)
                if value != '1':
                    logging.info('Set HTTP CN_CHECK = 1')
                    client.exec('HTTP CN_CHECK', 1)
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
    parser = argparse.ArgumentParser(description='iGS03E Auto Configuration Tool')
    parser.add_argument('--telnet', action='store_true', help='Use Telnet instead of SSH')
    parser.add_argument('--username', default='admin', help='Username (default: admin)')
    parser.add_argument('--password', default='admin', help='Password (default: admin)')
    args = parser.parse_args()

    protocol = 'telnet' if args.telnet else 'ssh'
    logger.info(f"Starting auto-config using {protocol} protocol")

    zeroconf = Zeroconf()
    listener = MyListener(username=args.username, password=args.password, protocol=protocol)
    browser = ServiceBrowser(zeroconf, "_ble-gw._tcp.local.", listener)
    try:
        input("Press enter to exit...\n\n")
    finally:
        zeroconf.close()
