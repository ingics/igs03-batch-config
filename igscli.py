import time
import getopt
import logging
try:
    import telnetlib
except ImportError:
    telnetlib = None
import socket
try:
    import paramiko
except ImportError:
    paramiko = None

logger = logging.getLogger()

# Suppress paramiko tracebacks in the output
if paramiko:
    logging.getLogger("paramiko").setLevel(logging.CRITICAL)

class IgsCmdError(Exception):
    def __init__(self, rst, cmd):
        self.rst = rst
        self.cmd = cmd
        super().__init__("\'%s\' return %d" % (self.cmd, self.rst))

class IgsBaseClient:
    def exec(self, cmd, *args, ignore_error_4=False, expect_close=False):
        raise NotImplementedError()

    def get(self, cmd):
        ans = self.exec(cmd)
        if '=' in ans:
            return ans.split('=')[1]
        return ans

    def reboot(self):
        return self.exec('REBOOT', expect_close=True)

    def reset(self):
        return self.exec('REBOOT DEFAULT', expect_close=True)

    def get_sys_info(self):
        data = self.exec('SYS INFO')
        info = {}
        for line in data.split('\n'):
            line = line.strip()
            if '=' in line:
                key, value = line.split('=', 1)
                info[key.strip()] = value.strip()
        return info

    def close(self):
        pass

class IgsTelnetClient(IgsBaseClient):
    def __init__(self, host, username, password, retry=5):
        if telnetlib is None:
            raise ImportError(
                "telnetlib is not available in this Python version (3.13+). "
                "Please install the backport: pip install telnetlib-313-and-up"
            )
        self.host = host
        self.client = telnetlib.Telnet(host)
        self.client.read_until(b'login:')
        self.client.write(username.encode() + b'\n')
        self.client.read_until(b'password:')
        self.client.write(password.encode() + b'\n')
        data = self.client.read_until(b'>', 3)
        if len(data) == 0 or data.decode('utf8', errors='ignore').strip() != '>':
            raise Exception('Wrong password or connection failed')

    def exec(self, cmd, *args, ignore_error_4=False, expect_close=False):
        if len(args) > 0:
            for arg in args:
                if isinstance(arg, (int, float)):
                    cmd = cmd + ' ' + str(arg)
                else:
                    cmd = cmd + ' "' + str(arg) + '"'
        try:
            self.client.write(cmd.encode() + b'\n')
            data_bytes = self.client.read_until(b'RESULT:')
            data = data_bytes.decode('utf8', errors='ignore')[:-7].strip()

            result_bytes = self.client.read_until(b'>')
            result_str = result_bytes.decode('utf8', errors='ignore')[:-1].strip()

            try:
                result = int(result_str)
            except ValueError:
                # Handle cases where parsing might fail
                logger.error(f"Failed to parse result code from: {result_str}")
                raise Exception(f"Invalid result format: {result_str}")

            if ignore_error_4 and result == 4:
                return ''
            elif result != 0:
                raise IgsCmdError(result, cmd)
            return data
        except EOFError as e:
            if expect_close:
                self.close()
                logger.log(logging.INFO, "Connection closed")
                return ''
            else:
                raise e

    def close(self):
        self.client.close()

class IgsSshClient(IgsBaseClient):
    def __init__(self, host, username, password):
        if paramiko is None:
            raise ImportError("paramiko is not installed")
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect(host, username=username, password=password,
                             look_for_keys=False, allow_agent=False, timeout=10)
        except Exception as e:
            raise e

        # Open an interactive shell session to mimic telnet behavior if needed,
        # but iGS works with exec_command for individual commands usually.
        # However, the prompt/result format might be easier to handle in a shell.
        self.shell = self.ssh.invoke_shell()
        self.shell.settimeout(5)
        # Wait for prompt
        self._read_until(b'>')

    def _read_until(self, expected, timeout=5):
        output = b""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.shell.recv_ready():
                char = self.shell.recv(1)
                output += char
                if output.endswith(expected):
                    return output
            time.sleep(0.01)
        return output

    def exec(self, cmd, *args, ignore_error_4=False, expect_close=False):
        if len(args) > 0:
            for arg in args:
                if isinstance(arg, (int, float)):
                    cmd = cmd + ' ' + str(arg)
                else:
                    cmd = cmd + ' "' + str(arg) + '"'

        try:
            self.shell.send(cmd + "\n")
            # iGS echo back the command? If so, we might need to skip it.
            # The current telnet code doesn't seem to worry about echo.

            data_bytes = self._read_until(b'RESULT:')
            # Strip the echo of the command if present (depends on shell config)
            data = data_bytes.decode('utf8', errors='ignore')[:-7].strip()
            if data.startswith(cmd):
                data = data[len(cmd):].strip()

            result_bytes = self._read_until(b'>')
            result_str = result_bytes.decode('utf8', errors='ignore')[:-1].strip()

            try:
                result = int(result_str)
            except ValueError:
                logger.error(f"Failed to parse result code from: {result_str}")
                raise Exception(f"Invalid result format: {result_str}")

            if ignore_error_4 and result == 4:
                return ''
            elif result != 0:
                raise IgsCmdError(result, cmd)
            # logger.debug(f"Raw data from {cmd}: {data!r}")
            return data
        except Exception as e:
            if expect_close:
                self.close()
                logger.log(logging.INFO, "Connection closed")
                return ''
            else:
                raise e

    def close(self):
        self.ssh.close()

def connect(host, username, password, protocol='ssh', retry=5):
    count = 1
    while count <= retry:
        logger.log(logging.INFO, 'Connecting to ' + host + ' via ' + protocol + ', try ' + str(count) + ' ...')

        try:
            if protocol == 'ssh':
                if paramiko is None:
                    raise ImportError("paramiko is not installed")
                client = IgsSshClient(host, username, password)
                logger.log(logging.INFO, 'Logged in via SSH...')
                return client
            elif protocol == 'telnet':
                client = IgsTelnetClient(host, username, password)
                logger.log(logging.INFO, 'Logged in via Telnet...')
                return client
            else:
                raise ValueError(f"Unsupported protocol: {protocol}")
        except (OSError, Exception) as e:
            logger.log(logging.ERROR, 'Fail to login, ' + str(e))

            # Don't retry if authentication failed
            if (paramiko and isinstance(e, paramiko.AuthenticationException)) or \
               (str(e) == 'Wrong password or connection failed'):
                raise e

            count += 1
            if count <= retry:
                time.sleep(3)
            else:
                raise e
