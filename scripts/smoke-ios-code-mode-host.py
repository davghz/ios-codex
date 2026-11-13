#!/usr/bin/env python3
"""Exercise the real host's framed protocol, V8 execution, state and tool callback."""
import json
import struct
import subprocess
import sys
import tempfile


def main():
    binary = sys.argv[1] if len(sys.argv) > 1 else '/var/jb/usr/libexec/codex-ios/codex-code-mode-host'
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen([binary, '--listen', 'stdio'], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=errors)
        delegate_calls = []

        def send(message):
            payload = json.dumps(message, separators=(',', ':')).encode()
            process.stdin.write(struct.pack('<I', len(payload)) + payload)
            process.stdin.flush()

        def read_exact(length):
            data = process.stdout.read(length)
            if len(data) != length:
                errors.seek(0)
                raise RuntimeError('Host disconnected: ' + errors.read().decode(errors='replace'))
            return data

        def receive():
            length = struct.unpack('<I', read_exact(4))[0]
            if length > 64 * 1024 * 1024:
                raise RuntimeError('Host exceeded the protocol frame size limit')
            return json.loads(read_exact(length))

        def response(kind, request_id):
            while True:
                message = receive()
                if message['type'] == 'delegate/request':
                    request = message['request']
                    assert request['type'] == 'tool/invoke', request
                    invocation = request['invocation']
                    assert invocation['tool_name'] == {'name': 'echo', 'namespace': None}, invocation
                    assert invocation['input'] == {'value': 42}, invocation
                    delegate_calls.append(invocation)
                    send({'type': 'delegate/response', 'id': message['id'], 'result': {
                        'status': 'ok', 'value': {'type': 'tool/result', 'result': {'echo': 42}}}})
                elif (message['type'] == 'operation/response' and message.get('id') == request_id
                      and message['result']['status'] == 'error'):
                    raise AssertionError(message)
                elif message['type'] == kind and message.get('id') == request_id:
                    assert message['result']['status'] == 'ok', message
                    return message['result']['value']
                elif message['type'] not in ('cell/closed', 'operation/response'):
                    raise AssertionError(message)

        def request(request_id, method, **fields):
            send({'type': 'operation/request', 'id': request_id, 'request': {
                'method': method, 'sessionId': 'ios-smoke', **fields}})

        def execute(request_id, source, tools):
            request(request_id, 'session/execute', request={
                'tool_call_id': f'smoke-{request_id}', 'enabled_tools': tools,
                'source': source, 'yield_time_ms': 60000, 'max_output_tokens': 1000})
            result = response('execute/initialResponse', request_id)['Result']
            assert result['error_text'] is None, result
            assert result['content_items'] == [{'type': 'input_text', 'text': '42'}], result

        try:
            send({'type': 'connection/hello', 'supportedVersions': [1],
                  'requiredCapabilities': [], 'optionalCapabilities': []})
            hello = receive()
            assert hello['type'] == 'connection/ready' and hello['selectedVersion'] == 1, hello
            request(1, 'session/open')
            assert response('operation/response', 1)['type'] == 'session/ready'
            execute(2, 'store("answer", 6 * 7); text(load("answer"));', [])
            tools = [{'name': 'echo', 'tool_name': {'name': 'echo', 'namespace': None},
                      'description': 'Return the smoke-test input', 'kind': 'function',
                      'input_schema': {'type': 'object', 'properties': {'value': {'type': 'integer'}}},
                      'output_schema': None}]
            execute(3, 'const value = await tools.echo({value: load("answer")}); text(value.echo);', tools)
            assert len(delegate_calls) == 1
            request(4, 'session/shutdown')
            assert response('operation/response', 4)['type'] == 'session/closed'
            process.stdin.close()
            assert process.wait() == 0
            print('PASS: native host protocol, V8 JavaScript, session storage, async tool callback')
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait()


if __name__ == '__main__':
    main()
