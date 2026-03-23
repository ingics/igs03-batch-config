# iGS03 Batch Configuration Tools

Tools for batch configuring Ingics iGS03 gateways via SSH (default) or Telnet.

## Setup

1. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/macOS
   ```

## Tools

### 1. Batch Configurator (`batch-config.py`)
This is the **main script** for batch configuring iGS03 devices that already have network settings and are accessible on your network.

**Usage:**
```bash
python batch-config.py <IP1> [IP2] ... [OPTIONS]
```
**Example:**
```bash
python batch-config.py 192.168.1.108 192.168.1.128 --username admin --password admin
```

### 2. iGS03E mDNS Configurator (`igs03e-batch-config-by-mdns.py`)
A specialized version for **iGS03E** devices. It uses mDNS to automatically discover devices on the local network and apply configuration as they appear.

> [!IMPORTANT]
> **CAUTION**: This script will automatically apply configuration settings to **ALL** iGS03E devices it discovers on the local network. Use with care.

**Usage:**
```bash
python igs03e-batch-config-by-mdns.py [OPTIONS]
```

**Protocol Auto-Detection:**
This tool automatically selects the connection protocol based on the device firmware version (V3.0.0+ uses SSH, otherwise Telnet). No manual protocol selection is required.

## Initial Configuration for New Devices
For new **iGS03W/iGS03M/iGS03MP** devices, you can follow these steps for initial setup:

1. **Power on** the iGS03W/M/MP device.
2. **Connect** to the device's WiFi AP manually (it usually creates an open AP).
3. **Run the batch configurator** with the default AP gateway address:
   ```bash
   python batch-config.py 192.168.10.1
   ```
4. **Repeat** steps 1-3 for each additional device.

## Customizing Commands
Both scripts are designed to be updated manually for your specific requirements. You must modify the **desired** commands in the source code.

For example, in `batch-config.py`:
```python
# modify these lines for your own settings
client.exec('MQTT CLIENTID', f'{model}_{identity}')
client.exec('MQTT PUBTOPIC', f'GNS_{identity}')
client.exec('BLE PAYLOADWD 1', 'XXFFXX008XBC')
```

## Options
- `--telnet`: Use Telnet protocol (SSH is the default).
- `--username`: Custom login username (default: `admin`).
- `--password`: Custom login password (default: `admin`).

## Notice
The scripts support SSH and Telnet. SSH is used for V3.0.0 and above firmware, and Telnet is used for legacy firmware.
These tools require Python 3.8+.
