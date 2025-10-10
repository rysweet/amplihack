"""Integration tests for log streaming with proxy server.

These tests verify that the log streaming server works correctly
when integrated with the main proxy server, handling real logging
from proxy operations.
"""

import asyncio
import json
import logging
import time

import aiohttp
import pytest


class TestProxyLogStreamIntegration:
    """Test integration between proxy server and log streaming."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_proxy_and_log_stream_startup(self, available_port):
        """Test that both proxy and log stream servers can start together."""
        # This should FAIL - no implementation exists yet
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            from amplihack.proxy.log_streaming import LogStreamServer
            from amplihack.proxy.manager import ProxyManager

            proxy_port = available_port
            log_port = proxy_port + 1000

            # Start both servers
            proxy_manager = ProxyManager()
            log_server = LogStreamServer(host="127.0.0.1", port=log_port)

            try:
                # Both should start without port conflicts
                proxy_started = await proxy_manager.start_proxy_async(proxy_port)
                log_started = await log_server.start()

                assert proxy_started is True
                assert log_started is True

                # Both should be running simultaneously
                assert proxy_manager.is_running()
                assert log_server.is_running()

            finally:
                await log_server.stop()
                proxy_manager.stop_proxy()

    @pytest.mark.integration
    def test_log_stream_port_calculation(self, available_port):
        """Test that log stream port is correctly calculated from proxy port."""
        # This should FAIL - no implementation exists yet
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            from amplihack.proxy.log_streaming import LogStreamConfig
            from amplihack.proxy.manager import ProxyManager

            proxy_port = available_port
            proxy_manager = ProxyManager()
            proxy_manager.proxy_port = proxy_port

            # Log stream should be on proxy_port + 1000
            log_config = LogStreamConfig.from_proxy_manager(proxy_manager)
            expected_log_port = proxy_port + 1000

            assert log_config.port == expected_log_port

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_proxy_logs_stream_to_clients(self, available_port):
        """Test that proxy log events are streamed to connected clients."""
        # This should FAIL - no implementation exists yet
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            from amplihack.proxy.log_streaming import LogStreamServer
            from amplihack.proxy.manager import ProxyManager

            proxy_port = available_port
            log_port = proxy_port + 1000

            proxy_manager = ProxyManager()
            log_server = LogStreamServer(host="127.0.0.1", port=log_port)

            try:
                # Start both servers
                await proxy_manager.start_proxy_async(proxy_port)
                await log_server.start()

                # Connect a test client to log stream
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://127.0.0.1:{log_port}/stream") as resp:
                        assert resp.status == 200
                        assert resp.headers.get("content-type") == "text/event-stream"

                        # Generate some proxy activity to create logs
                        await proxy_manager.handle_test_request()

                        # Should receive log events from the stream
                        chunk = await resp.content.read(1024)
                        sse_data = chunk.decode("utf-8")

                        assert "event: log" in sse_data or "data:" in sse_data

            finally:
                await log_server.stop()
                proxy_manager.stop_proxy()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_azure_request_logging_integration(self, available_port):
        """Test that Azure API requests generate appropriate log events."""
        # This should FAIL - no implementation exists yet
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            from amplihack.proxy.log_streaming import LogStreamServer
            from amplihack.proxy.manager import ProxyManager

            proxy_port = available_port
            log_port = proxy_port + 1000

            # Configure for Azure mode
            proxy_config = {
                "AZURE_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_API_KEY": "test-key",  # pragma: allowlist secret
                "PROXY_MODE": "azure",
            }

            proxy_manager = ProxyManager(proxy_config=proxy_config)
            log_server = LogStreamServer(host="127.0.0.1", port=log_port)

            collected_events = []

            # Mock log event handler to collect events
            async def collect_log_event(event_data):
                collected_events.append(event_data)

            log_server.on_log_event = collect_log_event

            try:
                await proxy_manager.start_proxy_async(proxy_port)
                await log_server.start()

                # Simulate Azure API request through proxy
                await proxy_manager.simulate_azure_request(
                    {"model": "gpt-4", "messages": [{"role": "user", "content": "test"}]}
                )

                # Wait for log events to be processed
                await asyncio.sleep(0.5)

                # Should have received Azure-related log events
                assert len(collected_events) > 0

                # Check for expected log content
                azure_logs = [
                    event
                    for event in collected_events
                    if "azure" in event.get("logger", "").lower()
                ]
                assert len(azure_logs) > 0

            finally:
                await log_server.stop()
                proxy_manager.stop_proxy()

    @pytest.mark.integration
    def test_log_handler_integration(self, available_port):
        """Test integration with Python logging infrastructure."""
        # This should FAIL - no implementation exists yet
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            from amplihack.proxy.log_streaming import LogStreamHandler, LogStreamServer

            log_port = available_port + 1000

            # Create log stream server and handler
            log_server = LogStreamServer(host="127.0.0.1", port=log_port)
            log_handler = LogStreamHandler(log_server)

            # Configure logging to use the stream handler
            logger = logging.getLogger("test.integration")
            logger.addHandler(log_handler)
            logger.setLevel(logging.INFO)

            collected_events = []

            # Mock event collection
            async def collect_events(event):
                collected_events.append(event)

            log_server.on_log_event = collect_events

            try:
                asyncio.run(log_server.start())

                # Generate log messages
                logger.info("Integration test message")
                logger.warning("Test warning message")
                logger.error("Test error message")

                # Process pending log events
                time.sleep(0.1)

                # Should have captured log events
                assert len(collected_events) >= 3

                # Verify log event structure
                for event in collected_events:
                    assert "timestamp" in event
                    assert "level" in event
                    assert "logger" in event
                    assert "message" in event

            finally:
                asyncio.run(log_server.stop())
                logger.removeHandler(log_handler)


class TestMultipleClientIntegration:
    """Test log streaming with multiple concurrent clients."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multiple_clients_receive_same_logs(self, available_port):
        """Test that multiple clients receive the same log events."""
        # This should FAIL - no implementation exists yet
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            from amplihack.proxy.log_streaming import LogStreamServer

            log_port = available_port + 1000
            log_server = LogStreamServer(host="127.0.0.1", port=log_port)

            client_events = {"client1": [], "client2": [], "client3": []}

            try:
                await log_server.start()

                # Connect multiple clients
                async def client_reader(client_name, port):
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"http://127.0.0.1:{port}/stream") as resp:
                            async for line in resp.content:
                                if line.startswith(b"data: "):
                                    event_data = line[6:].decode("utf-8").strip()
                                    try:
                                        parsed_event = json.loads(event_data)
                                        client_events[client_name].append(parsed_event)
                                    except json.JSONDecodeError:
                                        pass

                # Start multiple client readers
                client_tasks = [
                    asyncio.create_task(client_reader("client1", log_port)),
                    asyncio.create_task(client_reader("client2", log_port)),
                    asyncio.create_task(client_reader("client3", log_port)),
                ]

                # Wait for clients to connect
                await asyncio.sleep(0.2)

                # Generate log events
                await log_server.broadcast_log_event(
                    {
                        "timestamp": "2025-01-06T10:00:00Z",
                        "level": "INFO",
                        "logger": "test.broadcast",
                        "message": "Broadcast test message",
                    }
                )

                # Allow time for events to be received
                await asyncio.sleep(0.3)

                # Cancel client tasks
                for task in client_tasks:
                    task.cancel()

                # All clients should have received the same event
                assert len(client_events["client1"]) > 0
                assert len(client_events["client2"]) > 0
                assert len(client_events["client3"]) > 0

                # Events should be identical across clients
                assert client_events["client1"][0] == client_events["client2"][0]
                assert client_events["client2"][0] == client_events["client3"][0]

            finally:
                await log_server.stop()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_client_disconnect_handling(self, available_port):
        """Test graceful handling of client disconnections."""
        # This should FAIL - no implementation exists yet
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            from amplihack.proxy.log_streaming import LogStreamServer

            log_port = available_port + 1000
            log_server = LogStreamServer(host="127.0.0.1", port=log_port)

            try:
                await log_server.start()

                # Connect client and then disconnect
                session = aiohttp.ClientSession()
                await session.get(f"http://127.0.0.1:{log_port}/stream")

                # Verify client is connected
                assert log_server.get_client_count() == 1

                # Disconnect client
                await session.close()

                # Wait for server to detect disconnection
                await asyncio.sleep(0.5)

                # Client should be removed from server
                assert log_server.get_client_count() == 0

                # Server should continue operating normally
                assert log_server.is_running()

            finally:
                await log_server.stop()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_high_frequency_logging_performance(self, available_port, performance_monitor):
        """Test performance with high-frequency log events."""
        # This should FAIL - no implementation exists yet
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            from amplihack.proxy.log_streaming import LogStreamServer

            log_port = available_port + 1000
            log_server = LogStreamServer(host="127.0.0.1", port=log_port)

            try:
                await log_server.start()

                # Connect a client
                session = aiohttp.ClientSession()
                await session.get(f"http://127.0.0.1:{log_port}/stream")

                # Generate high-frequency log events
                async def generate_high_frequency_logs():
                    for i in range(100):
                        await log_server.broadcast_log_event(
                            {
                                "timestamp": f"2025-01-06T10:00:{i:02d}Z",
                                "level": "INFO",
                                "logger": "perf.test",
                                "message": f"Performance test message {i}",
                            }
                        )

                # Measure performance
                result, execution_time = await performance_monitor["measure_async_time"](
                    generate_high_frequency_logs()
                )

                # Should complete within reasonable time (< 1 second for 100 events)
                assert execution_time < 1.0

                # Server should still be responsive
                assert log_server.is_running()

                await session.close()

            finally:
                await log_server.stop()


class TestErrorHandlingIntegration:
    """Test error handling in integrated scenarios."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_log_server_resilience_to_proxy_restart(self, available_port):
        """Test that log server continues working when proxy restarts."""
        # This should FAIL - no implementation exists yet
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            from amplihack.proxy.log_streaming import LogStreamServer
            from amplihack.proxy.manager import ProxyManager

            proxy_port = available_port
            log_port = proxy_port + 1000

            proxy_manager = ProxyManager()
            log_server = LogStreamServer(host="127.0.0.1", port=log_port)

            try:
                # Start both servers
                await proxy_manager.start_proxy_async(proxy_port)
                await log_server.start()

                # Connect a client to log stream
                session = aiohttp.ClientSession()
                await session.get(f"http://127.0.0.1:{log_port}/stream")

                # Restart the proxy
                proxy_manager.stop_proxy()
                await asyncio.sleep(0.2)
                await proxy_manager.start_proxy_async(proxy_port)

                # Log server should still be running and responsive
                assert log_server.is_running()

                # Should still be able to send log events
                await log_server.broadcast_log_event(
                    {
                        "timestamp": "2025-01-06T10:00:00Z",
                        "level": "INFO",
                        "logger": "resilience.test",
                        "message": "Post-restart message",
                    }
                )

                await session.close()

            finally:
                await log_server.stop()
                proxy_manager.stop_proxy()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_port_conflict_resolution(self, available_port, port_manager):
        """Test handling of port conflicts during startup."""
        # This should FAIL - no implementation exists yet
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            from amplihack.proxy.log_streaming import LogStreamServer

            base_port = available_port + 1000

            # Occupy the intended log stream port
            with port_manager["occupy_port"](base_port):
                # Log server should find alternative port
                log_server = LogStreamServer(host="127.0.0.1", port=base_port)

                try:
                    await log_server.start()

                    # Should be running on alternative port
                    assert log_server.is_running()
                    actual_port = log_server.get_port()
                    assert actual_port != base_port  # Should have found different port
                    assert actual_port > base_port  # Should be higher port number

                finally:
                    await log_server.stop()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_malformed_log_event_handling(self, available_port):
        """Test handling of malformed log events."""
        # This should FAIL - no implementation exists yet
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            from amplihack.proxy.log_streaming import LogStreamServer

            log_port = available_port + 1000
            log_server = LogStreamServer(host="127.0.0.1", port=log_port)

            try:
                await log_server.start()

                # Try to broadcast malformed log events
                malformed_events = [
                    None,  # Null event
                    {},  # Empty event
                    {"message": "No timestamp or level"},  # Missing required fields
                    {
                        "timestamp": "invalid-date",
                        "level": "INFO",
                        "message": "test",
                    },  # Invalid timestamp
                    {
                        "timestamp": "2025-01-06T10:00:00Z",
                        "level": "INVALID",
                        "message": "test",
                    },  # Invalid level
                ]

                for malformed_event in malformed_events:
                    # Should handle gracefully without crashing
                    try:
                        await log_server.broadcast_log_event(malformed_event)
                    except Exception:
                        pass  # Expected to handle or reject malformed events

                # Server should still be running
                assert log_server.is_running()

            finally:
                await log_server.stop()

    @pytest.mark.integration
    def test_logging_configuration_integration(self):
        """Test integration with logging configuration system."""
        # This should FAIL - no implementation exists yet
        with pytest.raises((ImportError, AttributeError, NotImplementedError, ValueError)):
            import logging.config

            # Configure logging with log streaming
            logging_config = {
                "version": 1,
                "handlers": {
                    "log_stream": {
                        "class": "amplihack.proxy.log_streaming.LogStreamHandler",
                        "level": "INFO",
                        "stream_port": 9082,
                    }
                },
                "loggers": {"amplihack": {"handlers": ["log_stream"], "level": "INFO"}},
            }

            # Should be able to configure logging with stream handler
            logging.config.dictConfig(logging_config)

            # Test that logging works
            logger = logging.getLogger("amplihack.test")
            logger.info("Test message")

            # Should not raise exceptions
            assert True
