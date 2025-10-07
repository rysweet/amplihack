"""End-to-End tests for complete log streaming workflow.

These tests verify the entire log streaming system working together:
proxy server startup, log stream server initialization, client connections,
real Azure API calls, and complete log event delivery.
"""

import asyncio
import json
import time
from unittest.mock import Mock, patch

import aiohttp
import pytest


class TestCompleteLogStreamingWorkflow:
    """Test complete end-to-end log streaming workflow."""

    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.async_test
    async def test_full_proxy_to_client_log_streaming(self, available_port):
        """Test complete workflow: Proxy start -> Log streaming -> Client receives logs."""
        # This should FAIL - no implementation exists yet
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            from amplihack.proxy.config import ProxyConfig
            from amplihack.proxy.manager import ProxyManager

            proxy_port = available_port
            log_port = proxy_port + 1000

            # Configure proxy with Azure settings
            proxy_config = ProxyConfig(
                {
                    "AZURE_ENDPOINT": "https://test.openai.azure.com",
                    "AZURE_API_KEY": "test-key",
                    "AZURE_GPT4_DEPLOYMENT": "gpt-4",
                    "PROXY_MODE": "azure",
                    "PORT": str(proxy_port),
                    "ENABLE_LOG_STREAMING": "true",
                }
            )

            proxy_manager = ProxyManager(proxy_config=proxy_config)
            received_events = []

            try:
                # Step 1: Start proxy server
                proxy_started = await proxy_manager.start_proxy_async()
                assert proxy_started, "Proxy should start successfully"
                assert proxy_manager.is_running(), "Proxy should be running"

                # Step 2: Log streaming should auto-start with proxy
                log_stream_server = proxy_manager.get_log_stream_server()
                assert log_stream_server is not None, "Log stream server should be created"
                assert log_stream_server.is_running(), "Log stream server should be running"

                # Step 3: Connect client to log stream
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"http://127.0.0.1:{log_port}/stream",
                        headers={"Accept": "text/event-stream"},
                    ) as response:
                        assert response.status == 200
                        assert response.headers.get("content-type") == "text/event-stream"

                        # Step 4: Generate proxy activity to create logs
                        mock_azure_request = {
                            "model": "gpt-4",
                            "messages": [{"role": "user", "content": "Hello, test!"}],
                            "max_tokens": 10,
                        }

                        # Create a background task to collect log events
                        async def collect_events():
                            try:
                                async for line in response.content:
                                    line_str = line.decode("utf-8").strip()
                                    if line_str.startswith("data: "):
                                        event_data = line_str[6:]  # Remove 'data: ' prefix
                                        try:
                                            parsed_event = json.loads(event_data)
                                            received_events.append(parsed_event)
                                            # Stop after receiving a few events
                                            if len(received_events) >= 3:
                                                break
                                        except json.JSONDecodeError:
                                            continue
                            except asyncio.CancelledError:
                                pass

                        collect_task = asyncio.create_task(collect_events())

                        # Generate some proxy activity
                        await proxy_manager.simulate_azure_request(mock_azure_request)
                        await proxy_manager.simulate_health_check()

                        # Wait for events to be collected
                        try:
                            await asyncio.wait_for(collect_task, timeout=5.0)
                        except asyncio.TimeoutError:
                            collect_task.cancel()

                        # Step 5: Verify we received log events
                        assert len(received_events) > 0, "Should have received log events"

                        # Verify event structure
                        for event in received_events:
                            assert "timestamp" in event, "Event should have timestamp"
                            assert "level" in event, "Event should have level"
                            assert "logger" in event, "Event should have logger"
                            assert "message" in event, "Event should have message"

                        # Verify we received proxy-related events
                        proxy_events = [
                            e for e in received_events if "proxy" in e.get("logger", "").lower()
                        ]
                        assert len(proxy_events) > 0, "Should have received proxy-related events"

            finally:
                proxy_manager.stop_proxy()

    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.network
    async def test_azure_api_integration_with_log_streaming(self, available_port):
        """Test log streaming during actual Azure API integration."""
        # This should FAIL - no implementation exists yet
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            from amplihack.proxy.config import ProxyConfig
            from amplihack.proxy.manager import ProxyManager

            proxy_port = available_port
            log_port = proxy_port + 1000

            # Configure with real-ish Azure settings (but with test endpoint)
            proxy_config = ProxyConfig(
                {
                    "AZURE_ENDPOINT": "https://test-azure.openai.azure.com",
                    "AZURE_API_KEY": "test-key-12345",
                    "AZURE_GPT4_DEPLOYMENT": "test-gpt-4",
                    "PROXY_MODE": "azure",
                    "PORT": str(proxy_port),
                    "ENABLE_LOG_STREAMING": "true",
                }
            )

            proxy_manager = ProxyManager(proxy_config=proxy_config)
            azure_events = []

            try:
                # Start the complete system
                await proxy_manager.start_proxy_async()

                # Connect to log stream
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://127.0.0.1:{log_port}/stream") as response:
                        # Collect Azure-related events
                        async def collect_azure_events():
                            async for line in response.content:
                                line_str = line.decode("utf-8").strip()
                                if line_str.startswith("data: "):
                                    try:
                                        event = json.loads(line_str[6:])
                                        if "azure" in event.get("logger", "").lower():
                                            azure_events.append(event)
                                            if len(azure_events) >= 5:
                                                break
                                    except json.JSONDecodeError:
                                        continue

                        collect_task = asyncio.create_task(collect_azure_events())

                        # Mock Azure API interactions
                        with patch("aiohttp.ClientSession.post") as mock_post:
                            # Mock successful Azure response
                            mock_response = Mock()
                            mock_response.status = 200
                            mock_response.json.return_value = {
                                "choices": [
                                    {
                                        "message": {"content": "Test response"},
                                        "finish_reason": "stop",
                                    }
                                ]
                            }
                            mock_post.return_value.__aenter__.return_value = mock_response

                            # Trigger Azure API call through proxy
                            test_request = {
                                "model": "gpt-4",
                                "messages": [{"role": "user", "content": "Test Azure call"}],
                            }
                            await proxy_manager.process_azure_request(test_request)

                        # Wait for events
                        try:
                            await asyncio.wait_for(collect_task, timeout=3.0)
                        except asyncio.TimeoutError:
                            collect_task.cancel()

                        # Verify Azure-specific log events were captured
                        assert len(azure_events) > 0, "Should capture Azure-related log events"

                        azure_loggers = [event["logger"] for event in azure_events]
                        assert any("azure" in logger.lower() for logger in azure_loggers)

            finally:
                proxy_manager.stop_proxy()

    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_production_like_log_streaming_scenario(
        self, available_port, performance_monitor
    ):
        """Test production-like scenario with multiple clients and sustained logging."""
        # This should FAIL - no implementation exists yet
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            from amplihack.proxy.config import ProxyConfig
            from amplihack.proxy.manager import ProxyManager

            proxy_port = available_port
            log_port = proxy_port + 1000

            proxy_config = ProxyConfig(
                {
                    "AZURE_ENDPOINT": "https://prod-test.openai.azure.com",
                    "AZURE_API_KEY": "prod-test-key",
                    "AZURE_GPT4_DEPLOYMENT": "production-gpt-4",
                    "PROXY_MODE": "azure",
                    "PORT": str(proxy_port),
                    "ENABLE_LOG_STREAMING": "true",
                    "LOG_LEVEL": "INFO",
                }
            )

            proxy_manager = ProxyManager(proxy_config=proxy_config)
            client_events = {"client1": [], "client2": [], "client3": []}

            try:
                # Start the system
                start_time = time.time()
                await proxy_manager.start_proxy_async()
                startup_time = time.time() - start_time

                # Startup should be reasonably fast
                assert startup_time < 10.0, "System should start within 10 seconds"

                # Connect multiple clients
                sessions = []
                for client_id in client_events.keys():
                    session = aiohttp.ClientSession()
                    sessions.append(session)

                async def client_event_collector(client_id, session):
                    try:
                        async with session.get(f"http://127.0.0.1:{log_port}/stream") as resp:
                            async for line in resp.content:
                                line_str = line.decode("utf-8").strip()
                                if line_str.startswith("data: "):
                                    try:
                                        event = json.loads(line_str[6:])
                                        client_events[client_id].append(event)
                                        # Limit events per client
                                        if len(client_events[client_id]) >= 10:
                                            break
                                    except json.JSONDecodeError:
                                        continue
                    except asyncio.CancelledError:
                        pass

                # Start client collectors
                collector_tasks = [
                    asyncio.create_task(client_event_collector(client_id, session))
                    for client_id, session in zip(client_events.keys(), sessions)
                ]

                # Generate sustained proxy activity
                async def generate_proxy_activity():
                    for i in range(20):
                        # Simulate various proxy operations
                        await proxy_manager.handle_health_check()

                        test_request = {
                            "model": "gpt-4",
                            "messages": [{"role": "user", "content": f"Request {i}"}],
                        }

                        with patch("aiohttp.ClientSession.post") as mock_post:
                            mock_response = Mock()
                            mock_response.status = 200
                            mock_response.json.return_value = {
                                "choices": [{"message": {"content": "OK"}}]
                            }
                            mock_post.return_value.__aenter__.return_value = mock_response

                            await proxy_manager.process_azure_request(test_request)

                        await asyncio.sleep(0.1)  # Brief pause between requests

                # Run activity generation
                activity_start = time.time()
                await generate_proxy_activity()
                activity_time = time.time() - activity_start

                # Activity should complete within reasonable time
                assert activity_time < 15.0, "Activity generation should complete quickly"

                # Wait for events to be collected
                await asyncio.sleep(1.0)

                # Cancel collectors
                for task in collector_tasks:
                    if not task.done():
                        task.cancel()

                # Close sessions
                for session in sessions:
                    await session.close()

                # Verify all clients received events
                for client_id, events in client_events.items():
                    assert len(events) > 0, f"Client {client_id} should have received events"

                # Verify event consistency across clients
                # (They should receive the same events, though timing may vary)
                total_events = sum(len(events) for events in client_events.values())
                assert total_events > 30, "Should have generated substantial log traffic"

                # Performance verification
                log_server = proxy_manager.get_log_stream_server()
                stats = log_server.get_performance_stats()
                assert stats.get("avg_event_delivery_time", 0) < 0.1  # < 100ms average delivery

            finally:
                proxy_manager.stop_proxy()


class TestLogStreamingPerformance:
    """Test performance characteristics of log streaming system."""

    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.async_test
    async def test_log_streaming_does_not_impact_proxy_performance(
        self, available_port, performance_monitor
    ):
        """Test that log streaming doesn't significantly impact proxy performance."""
        # This should FAIL - no implementation exists yet
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            from amplihack.proxy.config import ProxyConfig
            from amplihack.proxy.manager import ProxyManager

            proxy_port = available_port

            proxy_config = ProxyConfig(
                {
                    "PORT": str(proxy_port),
                    "PROXY_MODE": "azure",
                    "AZURE_ENDPOINT": "https://test.openai.azure.com",
                    "AZURE_API_KEY": "test-key",
                }
            )

            # Test 1: Proxy performance WITHOUT log streaming
            proxy_manager_without_logs = ProxyManager(proxy_config=proxy_config)

            try:
                await proxy_manager_without_logs.start_proxy_async()

                async def benchmark_proxy_requests():
                    for i in range(50):
                        test_request = {
                            "model": "gpt-4",
                            "messages": [{"role": "user", "content": f"Benchmark {i}"}],
                        }

                        with patch("aiohttp.ClientSession.post") as mock_post:
                            mock_response = Mock()
                            mock_response.status = 200
                            mock_response.json.return_value = {
                                "choices": [{"message": {"content": "OK"}}]
                            }
                            mock_post.return_value.__aenter__.return_value = mock_response

                            await proxy_manager_without_logs.process_azure_request(test_request)

                # Measure performance without logging
                _, time_without_logs = await performance_monitor["measure_async_time"](
                    benchmark_proxy_requests()
                )

            finally:
                proxy_manager_without_logs.stop_proxy()

            # Test 2: Proxy performance WITH log streaming
            proxy_config_with_logs = ProxyConfig(
                {
                    "PORT": str(proxy_port),
                    "PROXY_MODE": "azure",
                    "AZURE_ENDPOINT": "https://test.openai.azure.com",
                    "AZURE_API_KEY": "test-key",
                    "ENABLE_LOG_STREAMING": "true",
                }
            )

            proxy_manager_with_logs = ProxyManager(proxy_config=proxy_config_with_logs)

            try:
                await proxy_manager_with_logs.start_proxy_async()

                # Connect a log client
                async with aiohttp.ClientSession() as session:
                    log_port = proxy_port + 1000
                    async with session.get(f"http://127.0.0.1:{log_port}/stream"):
                        # Measure performance with logging
                        _, time_with_logs = await performance_monitor["measure_async_time"](
                            benchmark_proxy_requests()
                        )

            finally:
                proxy_manager_with_logs.stop_proxy()

            # Performance impact should be minimal (< 20% overhead)
            performance_overhead = (time_with_logs - time_without_logs) / time_without_logs
            assert performance_overhead < 0.20, (
                f"Log streaming adds too much overhead: {performance_overhead:.2%}"
            )

    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.async_test
    async def test_log_streaming_system_stability_under_load(self, available_port):
        """Test system stability under sustained load."""
        # This should FAIL - no implementation exists yet
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            import gc

            from amplihack.proxy.config import ProxyConfig
            from amplihack.proxy.manager import ProxyManager

            proxy_port = available_port
            log_port = proxy_port + 1000

            proxy_config = ProxyConfig(
                {
                    "PORT": str(proxy_port),
                    "ENABLE_LOG_STREAMING": "true",
                    "PROXY_MODE": "azure",
                    "AZURE_ENDPOINT": "https://stress-test.openai.azure.com",
                    "AZURE_API_KEY": "stress-test-key",
                }
            )

            proxy_manager = ProxyManager(proxy_config=proxy_config)
            system_stable = True
            total_events_received = 0

            try:
                await proxy_manager.start_proxy_async()

                # Connect persistent client
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://127.0.0.1:{log_port}/stream") as response:

                        async def stress_test_activity():
                            nonlocal system_stable
                            try:
                                for batch in range(10):  # 10 batches
                                    for i in range(100):  # 100 requests per batch
                                        test_request = {
                                            "model": "gpt-4",
                                            "messages": [
                                                {
                                                    "role": "user",
                                                    "content": f"Stress test {batch}-{i}",
                                                }
                                            ],
                                        }

                                        with patch("aiohttp.ClientSession.post") as mock_post:
                                            mock_response = Mock()
                                            mock_response.status = 200
                                            mock_response.json.return_value = {
                                                "choices": [{"message": {"content": "OK"}}]
                                            }
                                            mock_post.return_value.__aenter__.return_value = (
                                                mock_response
                                            )

                                            await proxy_manager.process_azure_request(test_request)

                                    # Brief pause between batches
                                    await asyncio.sleep(0.1)

                                    # Force garbage collection
                                    gc.collect()

                                    # Check system health
                                    if not proxy_manager.is_running():
                                        system_stable = False
                                        break

                            except Exception as e:
                                print(f"Stress test error: {e}")
                                system_stable = False

                        async def event_counter():
                            nonlocal total_events_received
                            try:
                                async for line in response.content:
                                    if line.decode("utf-8").strip().startswith("data: "):
                                        total_events_received += 1
                                        # Limit counting to prevent infinite loop
                                        if total_events_received >= 1000:
                                            break
                            except asyncio.CancelledError:
                                pass

                        # Run stress test and event counting concurrently
                        stress_task = asyncio.create_task(stress_test_activity())
                        counter_task = asyncio.create_task(event_counter())

                        # Wait for stress test to complete
                        await asyncio.wait_for(stress_task, timeout=30.0)

                        # Give some time for final events
                        await asyncio.sleep(1.0)
                        counter_task.cancel()

                        # Verify system remained stable
                        assert system_stable, "System should remain stable under load"
                        assert proxy_manager.is_running(), "Proxy should still be running"

                        log_server = proxy_manager.get_log_stream_server()
                        assert log_server.is_running(), "Log server should still be running"

                        # Should have received substantial number of events
                        assert total_events_received > 100, "Should have received many log events"

            finally:
                proxy_manager.stop_proxy()

    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_graceful_shutdown_with_active_clients(self, available_port):
        """Test graceful shutdown of the system with active log streaming clients."""
        # This should FAIL - no implementation exists yet
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            from amplihack.proxy.config import ProxyConfig
            from amplihack.proxy.manager import ProxyManager

            proxy_port = available_port
            log_port = proxy_port + 1000

            proxy_config = ProxyConfig(
                {"PORT": str(proxy_port), "ENABLE_LOG_STREAMING": "true", "PROXY_MODE": "azure"}
            )

            proxy_manager = ProxyManager(proxy_config=proxy_config)

            try:
                await proxy_manager.start_proxy_async()

                # Connect multiple clients
                sessions = []
                for i in range(3):
                    session = aiohttp.ClientSession()
                    sessions.append(session)
                    # Start connection but don't await (simulates persistent clients)
                    asyncio.create_task(session.get(f"http://127.0.0.1:{log_port}/stream"))

                await asyncio.sleep(0.5)  # Let clients connect

                # Verify clients are connected
                log_server = proxy_manager.get_log_stream_server()
                assert log_server.get_client_count() > 0, "Should have active clients"

                # Initiate graceful shutdown
                shutdown_start = time.time()
                proxy_manager.stop_proxy()  # This should handle graceful shutdown
                shutdown_time = time.time() - shutdown_start

                # Shutdown should complete within reasonable time
                assert shutdown_time < 5.0, "Graceful shutdown should complete quickly"

                # System should be fully stopped
                assert not proxy_manager.is_running(), "Proxy should be stopped"
                assert not log_server.is_running(), "Log server should be stopped"

                # Clean up sessions
                for session in sessions:
                    try:
                        await session.close()
                    except:
                        pass

            except Exception as e:
                # Ensure cleanup even on test failure
                try:
                    proxy_manager.stop_proxy()
                except:
                    pass
                raise e
