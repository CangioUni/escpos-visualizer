"""Tests for DLE EOT (real-time paper status request) handling."""
import socket
import threading
import time
import unittest

from app import parse_escpos


class TestParseEscposDleEot(unittest.TestCase):
    """parse_escpos must silently skip DLE EOT sequences."""

    def test_dle_eot_skipped_mid_stream(self):
        """DLE EOT bytes embedded in a print stream are ignored by the parser."""
        data = bytearray()
        data.extend(b'Before')
        data.extend(b'\x10\x04\x04')  # DLE EOT 4 (paper sensor status request)
        data.extend(b'\nAfter\n')

        lines = parse_escpos(data)
        contents = [line['content'] for line in lines if line.get('type') == 'text']
        self.assertIn('Before', contents)
        self.assertIn('After', contents)
        # The DLE EOT bytes must not appear in any content
        for line in lines:
            content = line.get('content', '')
            self.assertNotIn('\x10', content)
            self.assertNotIn('\x04', content)

    def test_all_dle_eot_variants_skipped(self):
        """All four DLE EOT variants (n=1..4) are skipped."""
        for n in (1, 2, 3, 4):
            with self.subTest(n=n):
                data = bytearray(b'Hello')
                data.extend(bytes([0x10, 0x04, n]))
                data.extend(b'\n')
                lines = parse_escpos(data)
                contents = [line.get('content', '') for line in lines]
                self.assertTrue(any('Hello' in c for c in contents))

    def test_text_only_unaffected(self):
        """Streams without DLE EOT are parsed identically to before."""
        data = b'Test line\n'
        lines = parse_escpos(bytearray(data))
        self.assertEqual(lines[0]['content'], 'Test line')


class TestSocketPaperStatusResponse(unittest.TestCase):
    """The printer socket server must respond 0x12 to DLE EOT requests."""

    def _start_server_thread(self):
        """Import and wire up a minimal server socket for testing."""
        import app as app_module

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('127.0.0.1', 0))  # OS-assigned port
        server.listen(1)
        port = server.getsockname()[1]

        responses = []

        def handle():
            conn, _ = server.accept()
            try:
                raw_data = bytearray()
                pending = bytearray()
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    buf = pending + bytearray(chunk)
                    pending = bytearray()
                    i = 0
                    while i < len(buf):
                        if buf[i] == 0x10:
                            if i + 1 >= len(buf):
                                pending.extend(buf[i:])
                                break
                            if buf[i + 1] == 0x04:
                                if i + 2 >= len(buf):
                                    pending.extend(buf[i:])
                                    break
                                conn.send(app_module._PAPER_OK_STATUS)
                                responses.append(app_module._PAPER_OK_STATUS)
                                i += 3
                            else:
                                raw_data.append(buf[i])
                                i += 1
                        else:
                            raw_data.append(buf[i])
                            i += 1
                raw_data.extend(pending)
            except (ConnectionResetError, OSError):
                pass
            finally:
                conn.close()
                server.close()

        t = threading.Thread(target=handle, daemon=True)
        t.start()
        return port, t, responses

    def test_paper_status_response_is_0x12(self):
        """Server responds with 0x12 when DLE EOT 4 is received."""
        port, t, responses = self._start_server_thread()
        time.sleep(0.05)

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('127.0.0.1', port))
        client.send(b'\x10\x04\x04')  # DLE EOT 4 (paper sensor)
        time.sleep(0.05)
        client.close()
        t.join(timeout=2)

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0], bytes([0x12]))

    def test_multiple_status_requests_each_get_response(self):
        """Each DLE EOT in a stream gets its own 0x12 response."""
        port, t, responses = self._start_server_thread()
        time.sleep(0.05)

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('127.0.0.1', port))
        # Two status requests followed by normal print data
        client.send(b'\x10\x04\x01\x10\x04\x04Hello\n')
        time.sleep(0.05)
        client.close()
        t.join(timeout=2)

        self.assertEqual(len(responses), 2)
        for r in responses:
            self.assertEqual(r, bytes([0x12]))


if __name__ == '__main__':
    unittest.main()
