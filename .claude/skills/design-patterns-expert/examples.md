# Gang of Four Design Patterns - Production Examples

This file contains 10 real-world production examples demonstrating practical pattern applications.

---

## Example 1: Singleton for Configuration Management

**Pattern**: Singleton

**Scenario**: Application needs centralized configuration accessible from anywhere, loaded once at startup.

**Complete Code**:

```python
import json
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional


class Config:
    """
    Thread-safe singleton configuration manager.
    Loads configuration from JSON file once and provides global access.
    """
    _instance: Optional['Config'] = None
    _lock: Lock = Lock()
    _config: Dict[str, Any] = {}
    _loaded: bool = False

    def __new__(cls) -> 'Config':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, config_path: Path) -> None:
        """Load configuration from file (idempotent)."""
        if self._loaded:
            return

        with self._lock:
            if not self._loaded:
                with open(config_path, 'r') as f:
                    self._config = json.load(f)
                self._loaded = True

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Dictionary-style access."""
        return self._config[key]


# Usage
config = Config()
config.load(Path('config.json'))

# Access from anywhere in application
api_key = config.get('api_key')
database_url = config['database_url']
```

**Why This Pattern Works**:

- Configuration is read-only once loaded
- Truly global resource (single config file)
- Thread-safe initialization
- Performance benefit (load once, access many times)

**Trade-offs**:

- Global state (testing requires reset mechanism)
- Alternative: Dependency injection with config object
- Only justified because config is genuinely global and immutable after load

---

## Example 2: Factory Method for Plugin System

**Pattern**: Factory Method

**Scenario**: Application with extensible plugin system where plugins are discovered at runtime.

**Complete Code**:

```python
from abc import ABC, abstractmethod
from typing import Dict, Type
import importlib
import inspect


class Plugin(ABC):
    """Base plugin interface."""

    @abstractmethod
    def execute(self, data: dict) -> dict:
        """Execute plugin logic."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return plugin name."""
        pass


class DataTransformPlugin(Plugin):
    """Transforms data by converting keys to uppercase."""

    def execute(self, data: dict) -> dict:
        return {k.upper(): v for k, v in data.items()}

    def get_name(self) -> str:
        return "data_transform"


class DataValidationPlugin(Plugin):
    """Validates data has required keys."""

    def __init__(self, required_keys: list):
        self.required_keys = required_keys

    def execute(self, data: dict) -> dict:
        missing = [k for k in self.required_keys if k not in data]
        if missing:
            raise ValueError(f"Missing keys: {missing}")
        return data

    def get_name(self) -> str:
        return "data_validation"


class PluginFactory:
    """Factory for discovering and creating plugins."""

    def __init__(self):
        self._plugins: Dict[str, Type[Plugin]] = {}

    def register(self, plugin_class: Type[Plugin]) -> None:
        """Register a plugin class."""
        # Create temporary instance to get name
        temp = plugin_class() if not inspect.signature(plugin_class.__init__).parameters else None
        if temp:
            self._plugins[temp.get_name()] = plugin_class

    def create(self, plugin_name: str, **kwargs) -> Plugin:
        """Create plugin instance by name."""
        if plugin_name not in self._plugins:
            raise ValueError(f"Unknown plugin: {plugin_name}")
        return self._plugins[plugin_name](**kwargs)

    def discover(self, module_name: str) -> None:
        """Auto-discover plugins from module."""
        module = importlib.import_module(module_name)
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Plugin) and obj is not Plugin:
                self.register(obj)


# Usage
factory = PluginFactory()
factory.register(DataTransformPlugin)
factory.register(DataValidationPlugin)

# Create plugins dynamically
transform = factory.create("data_transform")
validator = factory.create("data_validation", required_keys=["id", "name"])

# Process data
data = {"id": 1, "name": "Alice"}
data = validator.execute(data)
data = transform.execute(data)
print(data)  # {'ID': 1, 'NAME': 'Alice'}
```

**Why This Pattern Works**:

- Multiple plugin types (≥2 concrete implementations)
- Plugins discovered/loaded dynamically at runtime
- Adding new plugins doesn't require changing factory code
- Clear separation: factory creates, plugins execute

**Trade-offs**:

- More complex than direct instantiation
- Only justified with multiple plugin types and dynamic loading requirements

---

## Example 3: Observer for Event-Driven Architecture

**Pattern**: Observer

**Scenario**: Real-time stock ticker where multiple components (UI, logger, analyzer) react to price updates.

**Complete Code**:

```python
from abc import ABC, abstractmethod
from typing import List, Dict
from datetime import datetime


class StockObserver(ABC):
    """Observer interface for stock price updates."""

    @abstractmethod
    def update(self, symbol: str, price: float, timestamp: datetime) -> None:
        """Called when stock price changes."""
        pass


class StockTicker:
    """Subject that notifies observers of price changes."""

    def __init__(self):
        self._observers: List[StockObserver] = []
        self._prices: Dict[str, float] = {}

    def attach(self, observer: StockObserver) -> None:
        """Add observer."""
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: StockObserver) -> None:
        """Remove observer."""
        self._observers.remove(observer)

    def set_price(self, symbol: str, price: float) -> None:
        """Update price and notify observers."""
        old_price = self._prices.get(symbol)
        if old_price != price:
            self._prices[symbol] = price
            self._notify(symbol, price)

    def _notify(self, symbol: str, price: float) -> None:
        """Notify all observers."""
        timestamp = datetime.now()
        for observer in self._observers:
            observer.update(symbol, price, timestamp)


class PriceLogger(StockObserver):
    """Logs all price changes."""

    def update(self, symbol: str, price: float, timestamp: datetime) -> None:
        print(f"[LOG] {timestamp}: {symbol} = ${price:.2f}")


class PriceAlertSystem(StockObserver):
    """Alerts when price exceeds threshold."""

    def __init__(self, threshold: float):
        self.threshold = threshold

    def update(self, symbol: str, price: float, timestamp: datetime) -> None:
        if price > self.threshold:
            print(f"[ALERT] {symbol} exceeded ${self.threshold}: ${price:.2f}")


class PriceAnalyzer(StockObserver):
    """Calculates moving average."""

    def __init__(self, window_size: int = 5):
        self.prices: Dict[str, List[float]] = {}
        self.window_size = window_size

    def update(self, symbol: str, price: float, timestamp: datetime) -> None:
        if symbol not in self.prices:
            self.prices[symbol] = []

        self.prices[symbol].append(price)
        if len(self.prices[symbol]) > self.window_size:
            self.prices[symbol].pop(0)

        avg = sum(self.prices[symbol]) / len(self.prices[symbol])
        print(f"[ANALYSIS] {symbol} MA({self.window_size}): ${avg:.2f}")


# Usage
ticker = StockTicker()

# Attach multiple observers
logger = PriceLogger()
alert = PriceAlertSystem(threshold=150.0)
analyzer = PriceAnalyzer(window_size=3)

ticker.attach(logger)
ticker.attach(alert)
ticker.attach(analyzer)

# Price updates automatically notify all observers
ticker.set_price("AAPL", 145.50)
ticker.set_price("AAPL", 147.20)
ticker.set_price("AAPL", 151.80)  # Triggers alert

# Can detach observers dynamically
ticker.detach(alert)
ticker.set_price("AAPL", 155.00)  # No alert
```

**Why This Pattern Works**:

- Multiple observers with different responsibilities (≥3)
- Dynamic observer set (attach/detach at runtime)
- One-to-many broadcast communication
- Observers are loosely coupled (don't know about each other)

**Trade-offs**:

- More complex than direct method calls
- Update order not guaranteed
- Need careful memory management (detach observers to prevent leaks)

---

## Example 4: Strategy for Payment Processing

**Pattern**: Strategy

**Scenario**: E-commerce checkout supporting multiple payment methods (credit card, PayPal, cryptocurrency).

**Complete Code**:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from decimal import Decimal


@dataclass
class PaymentResult:
    """Result of payment processing."""
    success: bool
    transaction_id: Optional[str] = None
    error_message: Optional[str] = None


class PaymentStrategy(ABC):
    """Strategy interface for payment processing."""

    @abstractmethod
    def process_payment(self, amount: Decimal, currency: str = "USD") -> PaymentResult:
        """Process payment and return result."""
        pass

    @abstractmethod
    def get_fee(self, amount: Decimal) -> Decimal:
        """Calculate processing fee."""
        pass


class CreditCardPayment(PaymentStrategy):
    """Credit card payment processing."""

    def __init__(self, card_number: str, cvv: str, expiry: str):
        self.card_number = card_number
        self.cvv = cvv
        self.expiry = expiry

    def process_payment(self, amount: Decimal, currency: str = "USD") -> PaymentResult:
        # Simulate credit card processing
        print(f"Processing ${amount} via credit card ****{self.card_number[-4:]}")
        return PaymentResult(
            success=True,
            transaction_id=f"CC-{self.card_number[-4:]}-12345"
        )

    def get_fee(self, amount: Decimal) -> Decimal:
        """Credit cards charge 2.9% + $0.30."""
        return amount * Decimal("0.029") + Decimal("0.30")


class PayPalPayment(PaymentStrategy):
    """PayPal payment processing."""

    def __init__(self, email: str):
        self.email = email

    def process_payment(self, amount: Decimal, currency: str = "USD") -> PaymentResult:
        print(f"Processing ${amount} via PayPal ({self.email})")
        return PaymentResult(
            success=True,
            transaction_id=f"PP-{self.email.split('@')[0]}-67890"
        )

    def get_fee(self, amount: Decimal) -> Decimal:
        """PayPal charges 2.9% + $0.30."""
        return amount * Decimal("0.029") + Decimal("0.30")


class CryptoPayment(PaymentStrategy):
    """Cryptocurrency payment processing."""

    def __init__(self, wallet_address: str, crypto_type: str = "BTC"):
        self.wallet_address = wallet_address
        self.crypto_type = crypto_type

    def process_payment(self, amount: Decimal, currency: str = "USD") -> PaymentResult:
        print(f"Processing ${amount} via {self.crypto_type} to {self.wallet_address[:8]}...")
        return PaymentResult(
            success=True,
            transaction_id=f"CRYPTO-{self.crypto_type}-ABCDEF"
        )

    def get_fee(self, amount: Decimal) -> Decimal:
        """Crypto charges flat $1.50 network fee."""
        return Decimal("1.50")


class CheckoutProcessor:
    """Context that uses payment strategy."""

    def __init__(self, payment_strategy: PaymentStrategy):
        self._strategy = payment_strategy

    def set_payment_method(self, payment_strategy: PaymentStrategy) -> None:
        """Change payment strategy at runtime."""
        self._strategy = payment_strategy

    def checkout(self, amount: Decimal) -> PaymentResult:
        """Process checkout with current payment strategy."""
        fee = self._strategy.get_fee(amount)
        total = amount + fee

        print(f"Order amount: ${amount}")
        print(f"Processing fee: ${fee}")
        print(f"Total: ${total}")

        return self._strategy.process_payment(total)


# Usage
order_amount = Decimal("99.99")

# Credit card payment
processor = CheckoutProcessor(
    CreditCardPayment(
        card_number="4532123456789012",
        cvv="123",
        expiry="12/25"
    )
)
result = processor.checkout(order_amount)
print(f"Result: {result}\n")

# Switch to PayPal
processor.set_payment_method(PayPalPayment(email="user@example.com"))
result = processor.checkout(order_amount)
print(f"Result: {result}\n")

# Switch to cryptocurrency
processor.set_payment_method(
    CryptoPayment(
        wallet_address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        crypto_type="BTC"
    )
)
result = processor.checkout(order_amount)
print(f"Result: {result}")
```

**Why This Pattern Works**:

- Multiple payment algorithms (≥3) with different implementations
- Need to switch payment methods at runtime
- Each strategy has different fee calculation logic
- Adding new payment methods doesn't change CheckoutProcessor

**Trade-offs**:

- More classes than simple if/else
- Only justified with ≥3 complex, swappable algorithms

---

## Example 5: Command for Undo/Redo in Text Editor

**Pattern**: Command

**Scenario**: Text editor supporting undo/redo for multiple operations (insert, delete, formatting).

**Complete Code**:

```python
from abc import ABC, abstractmethod
from typing import List


class Command(ABC):
    """Command interface with undo support."""

    @abstractmethod
    def execute(self) -> None:
        """Execute command."""
        pass

    @abstractmethod
    def undo(self) -> None:
        """Undo command."""
        pass


class TextDocument:
    """Receiver - the actual document."""

    def __init__(self):
        self.content = ""

    def insert(self, position: int, text: str) -> None:
        """Insert text at position."""
        self.content = self.content[:position] + text + self.content[position:]

    def delete(self, position: int, length: int) -> None:
        """Delete text from position."""
        self.content = self.content[:position] + self.content[position + length:]

    def __str__(self) -> str:
        return self.content


class InsertCommand(Command):
    """Command to insert text."""

    def __init__(self, document: TextDocument, position: int, text: str):
        self.document = document
        self.position = position
        self.text = text

    def execute(self) -> None:
        self.document.insert(self.position, self.text)

    def undo(self) -> None:
        self.document.delete(self.position, len(self.text))


class DeleteCommand(Command):
    """Command to delete text."""

    def __init__(self, document: TextDocument, position: int, length: int):
        self.document = document
        self.position = position
        self.length = length
        self.deleted_text = ""  # Save for undo

    def execute(self) -> None:
        # Save deleted text before deleting
        self.deleted_text = self.document.content[self.position:self.position + self.length]
        self.document.delete(self.position, self.length)

    def undo(self) -> None:
        self.document.insert(self.position, self.deleted_text)


class TextEditor:
    """Invoker with undo/redo support."""

    def __init__(self, document: TextDocument):
        self.document = document
        self.history: List[Command] = []
        self.redo_stack: List[Command] = []

    def execute_command(self, command: Command) -> None:
        """Execute command and add to history."""
        command.execute()
        self.history.append(command)
        self.redo_stack.clear()  # Clear redo stack on new command

    def undo(self) -> bool:
        """Undo last command."""
        if not self.history:
            return False

        command = self.history.pop()
        command.undo()
        self.redo_stack.append(command)
        return True

    def redo(self) -> bool:
        """Redo last undone command."""
        if not self.redo_stack:
            return False

        command = self.redo_stack.pop()
        command.execute()
        self.history.append(command)
        return True


# Usage
doc = TextDocument()
editor = TextEditor(doc)

# Perform operations
editor.execute_command(InsertCommand(doc, 0, "Hello"))
print(f"After insert 'Hello': {doc}")  # "Hello"

editor.execute_command(InsertCommand(doc, 5, " World"))
print(f"After insert ' World': {doc}")  # "Hello World"

editor.execute_command(DeleteCommand(doc, 5, 6))
print(f"After delete ' World': {doc}")  # "Hello"

# Undo operations
editor.undo()
print(f"After undo: {doc}")  # "Hello World"

editor.undo()
print(f"After undo: {doc}")  # "Hello"

# Redo operations
editor.redo()
print(f"After redo: {doc}")  # "Hello World"

editor.redo()
print(f"After redo: {doc}")  # "Hello"
```

**Why This Pattern Works**:

- Need undo/redo functionality
- Multiple command types with different undo logic
- Commands encapsulate all information needed for undo
- History management separate from command execution

**Trade-offs**:

- More complex than simple callbacks
- Memory overhead (storing command history)
- Only justified when undo/redo or command queuing needed

---

## Example 6: Adapter for Third-Party API Integration

**Pattern**: Adapter

**Scenario**: Application using different weather APIs (OpenWeather, WeatherAPI) with different interfaces.

**Complete Code**:

```python
from abc import ABC, abstractmethod
from typing import Dict
from dataclasses import dataclass


@dataclass
class WeatherData:
    """Unified weather data structure."""
    temperature_celsius: float
    humidity_percent: float
    description: str
    wind_speed_kmh: float


class WeatherService(ABC):
    """Target interface our application expects."""

    @abstractmethod
    def get_weather(self, city: str) -> WeatherData:
        """Get weather for city."""
        pass


# Third-party services (Adaptees) with different interfaces

class OpenWeatherAPI:
    """OpenWeather API with its own response format."""

    def fetch_current_weather(self, location: str) -> Dict:
        """Returns weather in OpenWeather format."""
        # Simulated API response
        return {
            "main": {
                "temp": 293.15,  # Kelvin
                "humidity": 65
            },
            "weather": [{"description": "partly cloudy"}],
            "wind": {"speed": 5.5}  # m/s
        }


class WeatherAPIService:
    """WeatherAPI.com with different response format."""

    def get_current_conditions(self, city_name: str) -> Dict:
        """Returns weather in WeatherAPI format."""
        # Simulated API response
        return {
            "temp_c": 20.0,
            "humidity": 65,
            "condition": {"text": "Partly cloudy"},
            "wind_kph": 19.8
        }


# Adapters

class OpenWeatherAdapter(WeatherService):
    """Adapter for OpenWeather API."""

    def __init__(self, api: OpenWeatherAPI):
        self.api = api

    def get_weather(self, city: str) -> WeatherData:
        """Convert OpenWeather response to WeatherData."""
        response = self.api.fetch_current_weather(city)

        # Convert Kelvin to Celsius
        temp_celsius = response["main"]["temp"] - 273.15

        # Convert m/s to km/h
        wind_kmh = response["wind"]["speed"] * 3.6

        return WeatherData(
            temperature_celsius=round(temp_celsius, 1),
            humidity_percent=response["main"]["humidity"],
            description=response["weather"][0]["description"],
            wind_speed_kmh=round(wind_kmh, 1)
        )


class WeatherAPIAdapter(WeatherService):
    """Adapter for WeatherAPI.com."""

    def __init__(self, api: WeatherAPIService):
        self.api = api

    def get_weather(self, city: str) -> WeatherData:
        """Convert WeatherAPI response to WeatherData."""
        response = self.api.get_current_conditions(city)

        return WeatherData(
            temperature_celsius=response["temp_c"],
            humidity_percent=response["humidity"],
            description=response["condition"]["text"],
            wind_speed_kmh=response["wind_kph"]
        )


class WeatherApp:
    """Application using unified WeatherService interface."""

    def __init__(self, weather_service: WeatherService):
        self.weather_service = weather_service

    def display_weather(self, city: str) -> None:
        """Display weather using unified interface."""
        weather = self.weather_service.get_weather(city)
        print(f"\nWeather in {city}:")
        print(f"  Temperature: {weather.temperature_celsius}°C")
        print(f"  Humidity: {weather.humidity_percent}%")
        print(f"  Conditions: {weather.description}")
        print(f"  Wind Speed: {weather.wind_speed_kmh} km/h")


# Usage
# Use OpenWeather API
openweather = OpenWeatherAPI()
adapter1 = OpenWeatherAdapter(openweather)
app = WeatherApp(adapter1)
app.display_weather("London")

# Switch to WeatherAPI.com
weatherapi = WeatherAPIService()
adapter2 = WeatherAPIAdapter(weatherapi)
app = WeatherApp(adapter2)
app.display_weather("Paris")
```

**Why This Pattern Works**:

- Third-party APIs we can't modify
- Different response formats need conversion
- Application code uses unified interface
- Easy to add new weather services

**Trade-offs**:

- Additional layer of indirection
- Only justified for external/unchangeable interfaces

---

## Example 7: Facade for Complex Subsystem (Video Encoding)

**Pattern**: Facade

**Scenario**: Video processing application with complex subsystems (codec, audio, metadata) providing simple interface.

**Complete Code**:

```python
from pathlib import Path
from typing import Optional


# Complex subsystem classes

class VideoCodec:
    """Handles video encoding/decoding."""

    def load_video(self, path: Path) -> bytes:
        print(f"[VideoCodec] Loading video from {path}")
        return b"video_data"

    def encode(self, data: bytes, codec: str, bitrate: int) -> bytes:
        print(f"[VideoCodec] Encoding video with {codec} at {bitrate}kbps")
        return b"encoded_video"


class AudioProcessor:
    """Handles audio processing."""

    def extract_audio(self, video_data: bytes) -> bytes:
        print("[AudioProcessor] Extracting audio track")
        return b"audio_data"

    def process_audio(self, audio_data: bytes, normalize: bool) -> bytes:
        if normalize:
            print("[AudioProcessor] Normalizing audio levels")
        return b"processed_audio"

    def merge_audio(self, video: bytes, audio: bytes) -> bytes:
        print("[AudioProcessor] Merging audio with video")
        return b"video_with_audio"


class MetadataEditor:
    """Handles video metadata."""

    def set_title(self, video: bytes, title: str) -> bytes:
        print(f"[MetadataEditor] Setting title: {title}")
        return video

    def set_description(self, video: bytes, description: str) -> bytes:
        print(f"[MetadataEditor] Setting description: {description}")
        return video

    def add_tags(self, video: bytes, tags: list) -> bytes:
        print(f"[MetadataEditor] Adding tags: {tags}")
        return video


class FileWriter:
    """Handles file output."""

    def save(self, data: bytes, path: Path, format: str) -> None:
        print(f"[FileWriter] Saving to {path} in {format} format")


# Facade

class VideoConverter:
    """
    Facade providing simple interface to complex video processing subsystem.
    Simplifies common video conversion workflow.
    """

    def __init__(self):
        self.codec = VideoCodec()
        self.audio = AudioProcessor()
        self.metadata = MetadataEditor()
        self.writer = FileWriter()

    def convert_video(
        self,
        input_path: Path,
        output_path: Path,
        target_codec: str = "h264",
        bitrate: int = 5000,
        normalize_audio: bool = True,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list] = None
    ) -> None:
        """
        Convert video with one simple method call.
        Handles all subsystem coordination automatically.
        """
        print(f"\n=== Converting {input_path} ===")

        # Load video
        video_data = self.codec.load_video(input_path)

        # Process audio
        audio_data = self.audio.extract_audio(video_data)
        audio_data = self.audio.process_audio(audio_data, normalize_audio)

        # Encode video
        encoded = self.codec.encode(video_data, target_codec, bitrate)

        # Merge audio back
        final_video = self.audio.merge_audio(encoded, audio_data)

        # Add metadata if provided
        if title:
            final_video = self.metadata.set_title(final_video, title)
        if description:
            final_video = self.metadata.set_description(final_video, description)
        if tags:
            final_video = self.metadata.add_tags(final_video, tags)

        # Save output
        output_format = output_path.suffix[1:]  # Remove leading dot
        self.writer.save(final_video, output_path, output_format)

        print(f"=== Conversion complete ===\n")


# Usage

# Without Facade - Complex (client must coordinate subsystems)
def convert_without_facade(input_path: Path, output_path: Path):
    codec = VideoCodec()
    audio = AudioProcessor()
    metadata = MetadataEditor()
    writer = FileWriter()

    video_data = codec.load_video(input_path)
    audio_data = audio.extract_audio(video_data)
    audio_data = audio.process_audio(audio_data, True)
    encoded = codec.encode(video_data, "h264", 5000)
    final = audio.merge_audio(encoded, audio_data)
    final = metadata.set_title(final, "My Video")
    writer.save(final, output_path, "mp4")


# With Facade - Simple (one line)
converter = VideoConverter()
converter.convert_video(
    input_path=Path("input.avi"),
    output_path=Path("output.mp4"),
    title="My Awesome Video",
    description="Converted with VideoConverter",
    tags=["tutorial", "python", "patterns"]
)
```

**Why This Pattern Works**:

- Complex subsystem with many interdependent classes (4+)
- Common workflow repeated frequently
- Clients don't need full subsystem control
- Simplifies client code dramatically

**Trade-offs**:

- May not expose all subsystem features
- Can become god object if overloaded
- Only justified when complexity exists (≥3 subsystem classes)

---

## Example 8: Decorator for Adding Features to Network Connections

**Pattern**: Decorator

**Scenario**: Network connection with optional features (encryption, compression, logging) that can be combined.

**Complete Code**:

```python
from abc import ABC, abstractmethod
import zlib
import base64


class Connection(ABC):
    """Component interface for network connections."""

    @abstractmethod
    def send(self, data: str) -> None:
        """Send data through connection."""
        pass

    @abstractmethod
    def receive(self) -> str:
        """Receive data from connection."""
        pass


class TCPConnection(Connection):
    """Concrete component - basic TCP connection."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.buffer = ""

    def send(self, data: str) -> None:
        """Send raw data."""
        print(f"[TCP] Sending to {self.host}:{self.port}: {data}")
        # Simulate sending - just store in buffer
        self.buffer = data

    def receive(self) -> str:
        """Receive raw data."""
        data = self.buffer
        print(f"[TCP] Receiving from {self.host}:{self.port}: {data}")
        return data


class ConnectionDecorator(Connection):
    """Base decorator."""

    def __init__(self, connection: Connection):
        self._connection = connection

    def send(self, data: str) -> None:
        self._connection.send(data)

    def receive(self) -> str:
        return self._connection.receive()


class EncryptedConnection(ConnectionDecorator):
    """Decorator adding encryption."""

    def send(self, data: str) -> None:
        encrypted = base64.b64encode(data.encode()).decode()
        print(f"[Encryption] Encrypting: {data} -> {encrypted}")
        self._connection.send(encrypted)

    def receive(self) -> str:
        encrypted = self._connection.receive()
        data = base64.b64decode(encrypted.encode()).decode()
        print(f"[Encryption] Decrypting: {encrypted} -> {data}")
        return data


class CompressedConnection(ConnectionDecorator):
    """Decorator adding compression."""

    def send(self, data: str) -> None:
        compressed = zlib.compress(data.encode())
        encoded = base64.b64encode(compressed).decode()
        print(f"[Compression] Compressing: {len(data)} -> {len(compressed)} bytes")
        self._connection.send(encoded)

    def receive(self) -> str:
        encoded = self._connection.receive()
        compressed = base64.b64decode(encoded.encode())
        data = zlib.decompress(compressed).decode()
        print(f"[Compression] Decompressing: {len(compressed)} -> {len(data)} bytes")
        return data


class LoggedConnection(ConnectionDecorator):
    """Decorator adding logging."""

    def send(self, data: str) -> None:
        print(f"[Logger] Logging send: {len(data)} bytes")
        self._connection.send(data)

    def receive(self) -> str:
        data = self._connection.receive()
        print(f"[Logger] Logging receive: {len(data)} bytes")
        return data


# Usage

# Basic connection
basic = TCPConnection("example.com", 8080)
basic.send("Hello World")
basic.receive()

print("\n" + "="*50 + "\n")

# Add encryption
encrypted = EncryptedConnection(TCPConnection("example.com", 8080))
encrypted.send("Secret Message")
encrypted.receive()

print("\n" + "="*50 + "\n")

# Combine multiple decorators: logging + encryption + compression
connection = LoggedConnection(
    EncryptedConnection(
        CompressedConnection(
            TCPConnection("example.com", 8080)
        )
    )
)

connection.send("This is a long message that will be compressed, encrypted, and logged!")
connection.receive()
```

**Why This Pattern Works**:

- Multiple optional features that can be combined (3+ decorators)
- Need to add/remove features dynamically at runtime
- Features are independent and composable
- Avoids explosion of subclasses (without decorator: 2^3 = 8 classes)

**Trade-offs**:

- Can result in many small objects
- Order of decoration matters
- Only justified with ≥3 combinable features

---

## Example 9: Composite for File System Hierarchy

**Pattern**: Composite

**Scenario**: File system where files and directories are treated uniformly (directories contain files/directories).

**Complete Code**:

```python
from abc import ABC, abstractmethod
from typing import List


class FileSystemItem(ABC):
    """Component interface for files and directories."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def get_size(self) -> int:
        """Get size in bytes."""
        pass

    @abstractmethod
    def display(self, indent: int = 0) -> None:
        """Display item with indentation."""
        pass


class File(FileSystemItem):
    """Leaf - represents a file."""

    def __init__(self, name: str, size: int):
        super().__init__(name)
        self.size = size

    def get_size(self) -> int:
        return self.size

    def display(self, indent: int = 0) -> None:
        print("  " * indent + f"📄 {self.name} ({self.size} bytes)")


class Directory(FileSystemItem):
    """Composite - represents a directory containing files/directories."""

    def __init__(self, name: str):
        super().__init__(name)
        self.children: List[FileSystemItem] = []

    def add(self, item: FileSystemItem) -> None:
        """Add file or directory."""
        self.children.append(item)

    def remove(self, item: FileSystemItem) -> None:
        """Remove file or directory."""
        self.children.remove(item)

    def get_size(self) -> int:
        """Calculate total size of all children."""
        return sum(child.get_size() for child in self.children)

    def display(self, indent: int = 0) -> None:
        """Display directory tree."""
        print("  " * indent + f"📁 {self.name}/ ({self.get_size()} bytes total)")
        for child in self.children:
            child.display(indent + 1)


# Usage

# Build file system structure
root = Directory("root")

# Documents folder
docs = Directory("documents")
docs.add(File("report.pdf", 2048))
docs.add(File("presentation.pptx", 4096))

# Projects folder
projects = Directory("projects")

# Python project
python_proj = Directory("python_app")
python_proj.add(File("main.py", 512))
python_proj.add(File("utils.py", 256))
python_proj.add(File("README.md", 128))

projects.add(python_proj)

# Web project
web_proj = Directory("website")
web_proj.add(File("index.html", 1024))
web_proj.add(File("style.css", 512))
web_proj.add(File("script.js", 768))

projects.add(web_proj)

# Build root structure
root.add(docs)
root.add(projects)
root.add(File("notes.txt", 256))

# Display entire tree
root.display()

# Get total size (works uniformly for files and directories)
print(f"\nTotal size: {root.get_size()} bytes")
print(f"Documents size: {docs.get_size()} bytes")
print(f"Python project size: {python_proj.get_size()} bytes")
```

**Why This Pattern Works**:

- Truly hierarchical/recursive structure (trees)
- Need to treat leaves and composites uniformly
- Operations work same way on both (get_size, display)
- Natural model for part-whole hierarchies

**Trade-offs**:

- Can make design overly general
- Type checking complications (all items treated uniformly)
- Only justified for genuine tree structures

---

## Example 10: Template Method for Data Processing Pipeline

**Pattern**: Template Method

**Scenario**: Data processing pipeline with fixed steps but algorithm-specific implementation details.

**Complete Code**:

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import json
import csv


class DataProcessor(ABC):
    """
    Abstract class defining template method for data processing pipeline.
    Defines algorithm skeleton, subclasses implement specific steps.
    """

    def process(self, input_path: str, output_path: str) -> None:
        """
        Template method defining processing pipeline.
        Steps executed in fixed order.
        """
        print(f"\n=== Processing {input_path} ===")

        # Step 1: Load data
        raw_data = self.load_data(input_path)
        print(f"Loaded {len(raw_data)} records")

        # Step 2: Validate (optional hook)
        if not self.validate_data(raw_data):
            raise ValueError("Data validation failed")

        # Step 3: Transform (required)
        transformed = self.transform_data(raw_data)
        print(f"Transformed to {len(transformed)} records")

        # Step 4: Filter (optional hook)
        filtered = self.filter_data(transformed)
        print(f"Filtered to {len(filtered)} records")

        # Step 5: Save
        self.save_data(filtered, output_path)
        print(f"Saved to {output_path}")

        # Step 6: Cleanup hook
        self.cleanup()

        print("=== Processing complete ===\n")

    # Abstract methods (must be implemented)

    @abstractmethod
    def load_data(self, path: str) -> List[Dict[str, Any]]:
        """Load data from source (implementation required)."""
        pass

    @abstractmethod
    def transform_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform data (implementation required)."""
        pass

    @abstractmethod
    def save_data(self, data: List[Dict[str, Any]], path: str) -> None:
        """Save data to destination (implementation required)."""
        pass

    # Hook methods (optional overrides)

    def validate_data(self, data: List[Dict[str, Any]]) -> bool:
        """
        Optional validation hook.
        Default: always valid. Override for custom validation.
        """
        return True

    def filter_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Optional filtering hook.
        Default: no filtering. Override for custom filtering.
        """
        return data

    def cleanup(self) -> None:
        """
        Optional cleanup hook.
        Default: no cleanup. Override for cleanup logic.
        """
        pass


class CSVToJSONProcessor(DataProcessor):
    """Concrete processor: CSV to JSON with uppercase transformation."""

    def load_data(self, path: str) -> List[Dict[str, Any]]:
        """Load from CSV file."""
        # Simulated CSV data
        return [
            {"name": "Alice", "age": "30", "city": "NYC"},
            {"name": "Bob", "age": "25", "city": "LA"},
            {"name": "Charlie", "age": "35", "city": "NYC"}
        ]

    def transform_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert all string values to uppercase."""
        return [
            {k: v.upper() if isinstance(v, str) else v for k, v in record.items()}
            for record in data
        ]

    def filter_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter: only include NYC residents."""
        return [record for record in data if record.get("city") == "NYC"]

    def save_data(self, data: List[Dict[str, Any]], path: str) -> None:
        """Save as JSON."""
        json_output = json.dumps(data, indent=2)
        print(f"JSON output:\n{json_output}")


class JSONToCSVProcessor(DataProcessor):
    """Concrete processor: JSON to CSV with age validation."""

    def load_data(self, path: str) -> List[Dict[str, Any]]:
        """Load from JSON file."""
        # Simulated JSON data
        return [
            {"name": "David", "age": 28, "salary": 50000},
            {"name": "Eve", "age": -5, "salary": 60000},  # Invalid age
            {"name": "Frank", "age": 32, "salary": 75000}
        ]

    def validate_data(self, data: List[Dict[str, Any]]) -> bool:
        """Validate all ages are positive."""
        for record in data:
            if record.get("age", 0) < 0:
                print(f"⚠️  Invalid age detected: {record}")
                return False
        return True

    def transform_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add 'senior' flag for age >= 30."""
        return [
            {**record, "senior": record.get("age", 0) >= 30}
            for record in data
        ]

    def save_data(self, data: List[Dict[str, Any]], path: str) -> None:
        """Save as CSV."""
        if data:
            fieldnames = data[0].keys()
            print(f"CSV output: {fieldnames}")
            for record in data:
                print(f"  {record}")


# Usage

# CSV to JSON processing
csv_processor = CSVToJSONProcessor()
csv_processor.process("input.csv", "output.json")

# JSON to CSV processing (will fail validation)
json_processor = JSONToCSVProcessor()
try:
    json_processor.process("input.json", "output.csv")
except ValueError as e:
    print(f"❌ Processing failed: {e}")

# Fix data and try again
class FixedJSONProcessor(JSONToCSVProcessor):
    def load_data(self, path: str) -> List[Dict[str, Any]]:
        data = super().load_data(path)
        # Fix invalid ages
        for record in data:
            if record.get("age", 0) < 0:
                record["age"] = 0
        return data

fixed_processor = FixedJSONProcessor()
fixed_processor.process("input.json", "output.csv")
```

**Why This Pattern Works**:

- Common algorithm structure with variant steps (5+ steps)
- Fixed execution order (template method controls flow)
- Multiple concrete processors with different implementations
- Mix of required methods and optional hooks

**Trade-offs**:

- Inverted control (subclasses don't call base, base calls subclasses)
- Less flexible than Strategy (can't swap algorithm at runtime)
- Only justified when algorithm has invariant parts and variant parts

---

## Summary

These 10 examples demonstrate:

1. **When patterns ARE justified**: Multiple variants (≥2-3), complex interactions, need for flexibility
2. **Production-ready code**: Complete implementations with error handling
3. **Philosophy-aligned**: Each example includes "Why This Works" and "Trade-offs" sections
4. **Real-world scenarios**: Configuration, plugins, events, payments, undo/redo, API integration, subsystems, features, hierarchies, pipelines

All examples follow amplihack's ruthless simplicity: patterns used only when complexity justifies them, with clear alternatives noted.
