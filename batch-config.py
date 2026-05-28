#!/usr/bin/env python

import sys
import time
import socket
import logging
import argparse
from igscli import connect

logging.basicConfig(
    stream = sys.stdout,
    level = logging.DEBUG,
    format = '[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger('__main__')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='iGS03 Batch Configuration Tool')
    parser.add_argument('--telnet', action='store_true', help='Use Telnet instead of SSH')
    parser.add_argument('--username', default='admin', help='Username (default: admin)')
    parser.add_argument('--password', default='admin', help='Password (default: admin)')
    parser.add_argument('--set-password', help='Set a new password for the device')
    parser.add_argument('gateways', nargs='+', help='Gateway IP addresses')
    args = parser.parse_args()

    protocol = 'telnet' if args.telnet else 'ssh'
    logger.info(f"Starting batch-config using {protocol} protocol")

    for IP in args.gateways:
        try:
            socket.inet_aton(IP)
        except socket.error:
            logger.error(f'Error: invalid IP address ({IP})')
            continue

        try:
            client = connect(IP, args.username, args.password, protocol=protocol)
            logger.info(f'Connected to {IP}')

            info = client.get_sys_info()
            mac = info.get('WIFI_MAC') or info.get('ETH_MAC', '')
            fw_ver = info.get('FIRMWARE_VERSION', '')

            if mac and fw_ver:
                # model from IGS03W-v3.0.6 -> IGS03W
                model = fw_ver.split('-')[0]

                # identity from 8C:4F:00:A0:21:30 -> 2130
                mac_fields = mac.split(':')
                identity = "".join(mac_fields[-2:])

                logger.info(f"Model: {model}, Identity: {identity}")

                # change password
                # Note: This will change the password for all future connections
                if (args.set_password):
                    client.exec('SYS PASSWORD', args.set_password)

                # example for change MQTT host
                client.exec('MQTT HOST', '192.168.1.31')
                # example for set MQTT client ID and topic to <model>_<identity>
                client.exec('MQTT CLIENTID', f'{model}_{identity}')
                client.exec('MQTT PUBTOPIC', f'{model}_{identity}')

                # example for enable bulk mode
                client.exec('MQTT BULKMODE', 1)
                # example for change payload whitelist entry #1
                client.exec('BLE PAYLOADWL 1', 'XXFFXX008XBC')
                # example for clear payload whitelist entry #2
                client.exec('BLE PAYLOADWL 2', '')
                # example for ble mac whitelist entry #1
                client.exec('BLE MACWL 1', '11AA22BB33DD')
                # example for clear ble whitelist entry #2
                client.exec('BLE MACWL 2', '')
            else:
                logger.error(f"Could not determine identity for {IP} from SYS INFO")

            client.close()
        except Exception as e:
            logger.error(f"Failed to configure device at {IP}: {e}")
