import threading
import socketserver
import queue


def multiplex(genlist):
    item_q = queue.Queue()
    def run_one(source, source_id):
        for item in source: item_q.put((source_id, item))

    def run_all():
        thrlist = []
        for (source_id, source) in enumerate(genlist) if isinstance(genlist, list) else genlist.items():
            t = threading.Thread(target=run_one,args=(source, source_id))
            t.start()
            thrlist.append(t)
        for t in thrlist: t.join()
        item_q.put(StopIteration)

    threading.Thread(target=run_all).start()
    while True:
        item = item_q.get()
        if item is StopIteration: return
        yield item


def tcp_server_source(host, port, block_size=1024):
    INIT = '@@qinit'
    main_queue = queue.Queue()

    class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
        def handle(self):
            main_queue.put(INIT)
            while True:
                try:
                    data = self.request.recv(block_size)
                    main_queue.put(data)
                    self.request.sendall(data)
                except:
                    return
        
        def finish(self):
            main_queue.put(None)


    class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        daemon_threads = True

    server = ThreadedTCPServer((host, port), ThreadedTCPRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    counter = 0
    while True:
        msg = main_queue.get()
        if msg == INIT: counter += 1
        elif not msg: counter -= 1
        else: yield msg
        main_queue.task_done()
        if not counter: break

    server.shutdown()
    server.server_close()