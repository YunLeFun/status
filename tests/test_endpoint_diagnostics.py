import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('diagnostics', Path(__file__).parents[1] / 'scripts/endpoint-diagnostics.py')
diagnostics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostics)


class EndpointDiagnosticsTests(unittest.TestCase):
    def test_keeps_dns_tcp_tls_first_byte_and_body_failures_distinct(self):
        cases = [
            (6, {}, 'dns'),
            (7, {}, 'tcp_connect'),
            (60, {}, 'tls'),
            (28, {}, 'dns_or_tcp_connect_timeout'),
            (28, {'time_connect': .1}, 'tls_handshake_timeout'),
            (28, {'time_connect': .1, 'time_appconnect': .2}, 'http_first_byte_timeout'),
            (28, {'time_connect': .1, 'time_appconnect': .2, 'time_starttransfer': .3}, 'response_body_timeout'),
        ]
        for exit_code, metrics, phase in cases:
            with self.subTest(phase=phase):
                self.assertEqual(diagnostics.failure_phase(exit_code, metrics), phase)

    def test_does_not_infer_failed_hop_from_accumulated_redirect_timings(self):
        metrics = {'num_redirects': 1, 'time_connect': .1, 'time_appconnect': .2, 'time_starttransfer': .3}
        self.assertEqual(diagnostics.failure_phase(28, metrics), 'timeout_during_redirect_chain_phase_unknown')

    def test_rejects_wrong_host_even_when_redirect_status_is_301(self):
        spec = diagnostics.ENDPOINTS[0]
        self.assertEqual(diagnostics.evaluate(spec, 0, {'http_code': 301}, ['location: https://other.example/']),
                         (False, 'unexpected_redirect_target'))
        self.assertEqual(diagnostics.evaluate(spec, 0, {'http_code': 301}, ['location: https://www.yunle.fun/']),
                         (True, None))

    def test_rejects_redirect_loop_or_wrong_chain_destination(self):
        spec = diagnostics.ENDPOINTS[2]
        for metrics in [{'http_code': 200, 'num_redirects': 2, 'url_effective': 'https://www.yunle.fun/'},
                        {'http_code': 200, 'num_redirects': 1, 'url_effective': 'https://other.example/'}]:
            self.assertEqual(diagnostics.evaluate(spec, 0, metrics, []), (False, 'unexpected_redirect_chain'))

    def test_does_not_treat_application_errors_as_healthy(self):
        self.assertEqual(diagnostics.evaluate(diagnostics.ENDPOINTS[1], 0, {'http_code': 503}, []),
                         (False, 'unexpected_http_status'))

    def test_logs_only_allowlisted_headers(self):
        raw = 'HTTP/2 301\r\nLocation: https://www.yunle.fun/\r\nSet-Cookie: private=fake\r\nAuthorization: fake\r\nEO-Log-UUID: 123\r\n'
        self.assertEqual(diagnostics.summarize_headers(raw),
                         ['HTTP/2 301', 'Location: https://www.yunle.fun/', 'EO-Log-UUID: 123'])


if __name__ == '__main__':
    unittest.main()
