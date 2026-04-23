# Alternate ``w`` implementation kept in-tree for reference. It is **not** listed in
# ``commands.__all__`` so ``rpi_ground.Command_w_gt`` / ``base.Command_w`` stay authoritative.
from cowrie.shell.command import HoneyPotCommand
import random
from datetime import datetime

commands = {}

FAKE_SESSIONS = None

class Command_w(HoneyPotCommand):
    def call(self):
        global FAKE_SESSIONS

        real_ip = self.protocol.clientIP

        # Generate once
        if FAKE_SESSIONS is None:
            sessions = []
            used_ips = {real_ip}

            # Attacker session
            sessions.append(
                f"{'pi':<8} {'pts/0':<8} {real_ip:<15} 14:32   0.00s  0.03s 0.03s -bash"
            )

            # Add 1–2 extra users
            num_extra = random.randint(1, 2)

            for i in range(1, num_extra + 1):
                while True:
                    ip = f"10.4.27.{random.randint(30,80)}"
                    if ip not in used_ips:
                        used_ips.add(ip)
                        break

                login_time = f"{random.randint(10,23):02d}:{random.randint(0,59):02d}"
                idle = random.choice(["5.00s", "12:56", "4:31m"])
                what = random.choice(["-bash", "top", "sudo su"])

                sessions.append(
                    f"{'pi':<8} {f'pts/{i}':<8} {ip:<15} {login_time:<7} {idle:<6} 0.03s 0.03s {what}"
                )

            FAKE_SESSIONS = sessions

        # Reuse sessions
        num_users = len(FAKE_SESSIONS)

        header = f"{datetime.now().strftime('%H:%M:%S')} up 1 day,  {num_users} users,  load average: 0.00, 0.00, 0.00"
        columns = "USER     TTY      FROM           LOGIN@   IDLE   JCPU   PCPU WHAT"

        self.write(header + "\n")
        self.write(columns + "\n")

        for s in FAKE_SESSIONS:
            self.write(s + "\n")
            
commands["/bin/w"] = Command_w
commands["w"] = Command_w
            


