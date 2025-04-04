import queue
import concurrent.futures
from mcrcon import MCRcon

class RCONConnectionPool:
    def __init__(self, host, password, port, pool_size):
        self.pool = queue.Queue()
        self.host = host
        self.password = password
        self.port = port
        for _ in range(pool_size):
            conn = MCRcon(host, password, port=port)
            conn.connect()
            self.pool.put(conn)
    
    def get(self):
        return self.pool.get()
    
    def put(self, conn):
        self.pool.put(conn)
    
    def close_all(self):
        while not self.pool.empty():
            conn = self.pool.get()
            conn.disconnect()

def send_commands(commands, host, port, password, pool_size=16):
    """
    Sends a list of setblock commands to the Minecraft server using a connection pool.
    """
    pool = RCONConnectionPool(host, password, port, pool_size)

    def send_block_command(cmd):
        conn = pool.get()
        try:
            return conn.command(cmd)
        finally:
            pool.put(conn)

    print(f"Sending {len(commands)} setblock commands using a connection pool...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=pool_size) as executor:
        results = list(executor.map(send_block_command, commands))
    pool.close_all()
    print("Done placing the image in 3D!")
    return results
