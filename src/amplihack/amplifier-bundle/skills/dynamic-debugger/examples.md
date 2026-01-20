# Dynamic Debugger Examples

Production-ready debugging examples fer all supported languages. Each example shows a complete workflow from problem to resolution.

## Python: Async Function Not Awaiting

### Problem

Async function returns coroutine instead of actual value:

```python
# user_service.py
import asyncio
import aiohttp

async def fetch_user(user_id: int):
    """Fetch user from API."""
    async with aiohttp.ClientSession() as session:
        url = f"https://api.example.com/users/{user_id}"
        async with session.get(url) as response:
            return await response.json()

async def get_user_email(user_id: int):
    """Get user email - BUG HERE."""
    user = fetch_user(user_id)  # Missing await!
    return user.get("email")  # TypeError: coroutine object is not subscriptable

async def main():
    email = await get_user_email(123)
    print(f"User email: {email}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Debugging Session

**User:** "Why is get_user_email failing? Debug this."

**Skill Response:**

```
🔍 Debugging intent detected (high confidence)
🐍 Language: Python (detected from .py extension)
🚀 Starting debugpy session...

✅ Debugger ready. Setting breakpoint at get_user_email...
```

**Set Breakpoint:**

```
Set breakpoint at line 14
```

**Skill Response:**

```
✓ Breakpoint set at user_service.py:14 (get_user_email)
▶ Running until breakpoint...

🛑 Paused at user_service.py:14
   13: async def get_user_email(user_id: int):
→  14:     user = fetch_user(user_id)
   15:     return user.get("email")
```

**Inspect Variable:**

```
What's the value of user after line 14?
```

**Skill Response:**

```
Variable: user
Type: <coroutine object fetch_user>
Value: <coroutine object fetch_user at 0x7f8b3c4d5e40>

⚠️ Issue detected: 'user' is a coroutine, not a dict!
💡 Hint: Missing 'await' keyword before fetch_user(user_id)
```

**Step Into:**

```
Show me the code around line 14
```

**Skill Response:**

```
   13: async def get_user_email(user_id: int):
→  14:     user = fetch_user(user_id)  # 🐛 Missing await!
   15:     return user.get("email")

🔍 Analysis: fetch_user() is async but not awaited
✅ Fix: Change to: user = await fetch_user(user_id)
```

### Solution

```python
async def get_user_email(user_id: int):
    """Get user email - FIXED."""
    user = await fetch_user(user_id)  # ✅ Added await
    return user.get("email")
```

**Verification:**

```
Stop debugging
```

**Skill Response:**

```
✓ Debugging session ended
📊 Session summary:
   - Breakpoints: 1
   - Steps executed: 2
   - Variables inspected: 1
   - Duration: 45 seconds

✅ Fix identified: Missing await keyword
```

## JavaScript: Promise Chain Not Resolving

### Problem

Promise chain hangs because error not caught:

```javascript
// order_processor.js
const axios = require("axios");

function validateOrder(orderId) {
  return axios.get(`https://api.example.com/orders/${orderId}`).then((response) => {
    if (response.data.status !== "pending") {
      throw new Error(`Order ${orderId} is not pending`);
    }
    return response.data;
  });
}

function processPayment(order) {
  return axios
    .post("https://api.example.com/payments", {
      orderId: order.id,
      amount: order.total,
    })
    .then((response) => response.data);
}

function fulfillOrder(orderId) {
  return validateOrder(orderId)
    .then((order) => processPayment(order))
    .then((payment) => {
      console.log(`Payment processed: ${payment.id}`);
      return payment;
    });
  // BUG: No .catch() - errors are swallowed
}

fulfillOrder(12345)
  .then((result) => console.log("Order fulfilled:", result))
  .catch((err) => console.error("Failed:", err));
```

### Debugging Session

**User:** "fulfillOrder Promise isn't resolving. Set breakpoints."

**Skill Response:**

```
🔍 Explicit debugging trigger detected
📜 Language: JavaScript (detected from package.json)
🚀 Starting Node debugger on port 9229...

✅ Debugger attached
```

**Set Multiple Breakpoints:**

```
Set breakpoint at line 18
Set breakpoint at line 25
Set breakpoint at line 29
```

**Skill Response:**

```
✓ Breakpoint 1: order_processor.js:18 (validateOrder then-handler)
✓ Breakpoint 2: order_processor.js:25 (processPayment then-handler)
✓ Breakpoint 3: order_processor.js:29 (fulfillOrder then-handler)

▶ Running until first breakpoint...

🛑 Paused at order_processor.js:18
   17:     .then(response => {
→  18:       if (response.data.status !== 'pending') {
   19:         throw new Error(`Order ${orderId} is not pending`);
```

**Inspect Response:**

```
What's response.data.status?
```

**Skill Response:**

```
Variable: response.data.status
Type: string
Value: "completed"

⚠️ Order status is "completed", not "pending"
💡 Exception will be thrown at line 19
```

**Continue:**

```
Continue
```

**Skill Response:**

```
💥 Exception thrown: Error: Order 12345 is not pending
   at order_processor.js:19

🔍 Call stack:
   1. validateOrder.then (order_processor.js:19)
   2. fulfillOrder (order_processor.js:24)
   3. <anonymous> (order_processor.js:34)

⚠️ Analysis: No .catch() handler in fulfillOrder()
   Exception is uncaught and Promise hangs!
```

### Solution

```javascript
function fulfillOrder(orderId) {
  return validateOrder(orderId)
    .then((order) => processPayment(order))
    .then((payment) => {
      console.log(`Payment processed: ${payment.id}`);
      return payment;
    })
    .catch((err) => {
      // ✅ Added catch handler
      console.error(`Order ${orderId} failed:`, err.message);
      throw err; // Re-throw for caller to handle
    });
}
```

## C++: Segmentation Fault Investigation

### Problem

Segfault when accessing freed memory:

```cpp
// user_manager.cpp
#include <iostream>
#include <string>
#include <vector>

class User {
public:
    std::string name;
    int id;

    User(std::string n, int i) : name(n), id(i) {}
};

User* createUser(std::string name, int id) {
    User user(name, id);
    return &user;  // BUG: Returning address of local variable!
}

std::vector<User*> loadUsers() {
    std::vector<User*> users;
    users.push_back(createUser("Alice", 1));
    users.push_back(createUser("Bob", 2));
    users.push_back(createUser("Charlie", 3));
    return users;
}

int main() {
    std::vector<User*> users = loadUsers();

    for (User* user : users) {
        std::cout << "User: " << user->name << std::endl;  // Segfault here!
    }

    return 0;
}
```

### Debugging Session

**User:** "Getting segfault in user->name access. Debug with gdb."

**Skill Response:**

```
🔍 Debugging intent detected
⚙️ Language: C++ (detected from .cpp extension)
🚀 Starting gdb session...

✅ Debugger ready
⚠️ Compile with debug symbols: g++ -g user_manager.cpp -o user_manager
```

**Run Until Crash:**

```
Continue
```

**Skill Response:**

```
💥 Segmentation fault (SIGSEGV)

Program received signal SIGSEGV, Segmentation fault.
0x0000555555555289 in main () at user_manager.cpp:30

   29:     for (User* user : users) {
→  30:         std::cout << "User: " << user->name << std::endl;
   31:     }

📍 Crash location: user_manager.cpp:30
```

**Show Call Stack:**

```
Show call stack
```

**Skill Response:**

```
📚 Call stack:
   #0  main () at user_manager.cpp:30
   #1  __libc_start_main () from /lib/x86_64-linux-gnu/libc.so.6

🔍 Local variables at crash:
   users = std::vector<User*> (size=3)
   user = 0x7fffffffdcc0 (invalid address)
```

**Inspect Pointer:**

```
What's the value of user?
```

**Skill Response:**

```
Variable: user
Type: User*
Value: 0x7fffffffdcc0
   ↳ name: <invalid memory>
   ↳ id: <invalid memory>

⚠️ Pointer points to invalid memory!
💡 Likely cause: Dangling pointer to local variable
```

**Inspect createUser:**

```
Show me createUser function
```

**Skill Response:**

```
   13: User* createUser(std::string name, int id) {
   14:     User user(name, id);
→  15:     return &user;  // 🐛 CRITICAL BUG!
   16: }

🚨 BUG FOUND: Returning address of local variable!
   Variable 'user' is destroyed when function returns.
   Pointer becomes dangling immediately.

✅ Fix: Return User by value or allocate on heap
```

### Solution

**Option 1: Return by value (preferred):**

```cpp
User createUser(std::string name, int id) {
    return User(name, id);  // ✅ Return by value
}

std::vector<User> loadUsers() {  // Store values, not pointers
    std::vector<User> users;
    users.push_back(createUser("Alice", 1));
    users.push_back(createUser("Bob", 2));
    users.push_back(createUser("Charlie", 3));
    return users;
}
```

**Option 2: Heap allocation (if pointers needed):**

```cpp
User* createUser(std::string name, int id) {
    return new User(name, id);  // ✅ Heap allocation
}

// Remember to delete in caller!
for (User* user : users) {
    std::cout << "User: " << user->name << std::endl;
    delete user;  // ✅ Clean up
}
```

## Go: Goroutine Deadlock

### Problem

Goroutines deadlocked on channel operations:

```go
// worker_pool.go
package main

import (
    "fmt"
    "sync"
)

func worker(id int, jobs <-chan int, results chan<- int) {
    for job := range jobs {
        fmt.Printf("Worker %d processing job %d\n", id, job)
        results <- job * 2  // Send result
    }
}

func main() {
    jobs := make(chan int)      // BUG: Unbuffered channel
    results := make(chan int)   // BUG: Unbuffered channel

    var wg sync.WaitGroup

    // Start 3 workers
    for i := 1; i <= 3; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            worker(id, jobs, results)
        }(i)
    }

    // Send 10 jobs
    for j := 1; j <= 10; j++ {
        jobs <- j  // BUG: Blocks because no receiver yet!
    }
    close(jobs)

    // Receive results
    for i := 1; i <= 10; i++ {
        result := <-results
        fmt.Printf("Result: %d\n", result)
    }

    wg.Wait()
}
```

### Debugging Session

**User:** "Goroutines deadlocked. Need to trace execution."

**Skill Response:**

```
🔍 Debugging intent detected
🔷 Language: Go (detected from go.mod)
🚀 Starting delve session on port 2345...

✅ Debugger ready
```

**Set Breakpoint at Deadlock:**

```
Set breakpoint at line 28
```

**Skill Response:**

```
✓ Breakpoint set at worker_pool.go:28 (main function)

▶ Running...

🛑 Paused at worker_pool.go:28
   27:     // Send 10 jobs
→  28:     for j := 1; j <= 10; j++ {
   29:         jobs <- j
   30:     }
```

**Step Into:**

```
Step over
```

**Skill Response:**

```
⏸️ Execution blocked at line 29: jobs <- j

🔒 DEADLOCK DETECTED!
   All goroutines are asleep - no way to make progress

📊 Goroutine status:
   Goroutine 1 (main):    Blocked sending on channel 'jobs'
   Goroutine 2 (worker 1): Blocked receiving on channel 'jobs'
   Goroutine 3 (worker 2): Blocked receiving on channel 'jobs'
   Goroutine 4 (worker 3): Blocked receiving on channel 'jobs'
```

**Inspect Channels:**

```
What's the state of jobs channel?
```

**Skill Response:**

```
Channel: jobs
Type: chan int
Capacity: 0 (unbuffered)
Queue length: 0
Send waiters: 1 (goroutine 1 - main)
Receive waiters: 3 (goroutines 2, 3, 4 - workers)

🔍 Analysis:
   - Main goroutine trying to send
   - Workers waiting to receive
   - BUT: Workers waiting on range loop, which needs channel closed
   - Channel not closed because send loop hasn't finished!

🐛 CLASSIC DEADLOCK PATTERN:
   1. Main sends to jobs channel (blocks until received)
   2. Workers can't receive until channel closed
   3. Channel can't close until sends finish
   4. Sends can't finish because workers not receiving
   → Circular dependency!
```

### Solution

**Option 1: Send in separate goroutine:**

```go
// Send jobs in background goroutine
go func() {
    for j := 1; j <= 10; j++ {
        jobs <- j
    }
    close(jobs)  // ✅ Close after all sends
}()

// Receive results in main goroutine
for i := 1; i <= 10; i++ {
    result := <-results
    fmt.Printf("Result: %d\n", result)
}

wg.Wait()
```

**Option 2: Buffered channels:**

```go
jobs := make(chan int, 10)      // ✅ Buffer size matches job count
results := make(chan int, 10)   // ✅ Buffer for results

// Now sends won't block
for j := 1; j <= 10; j++ {
    jobs <- j
}
close(jobs)
```

## Rust: Panic in Match Statement

### Problem

Panic when matching enum variant with unexpected data:

```rust
// payment_processor.rs
#[derive(Debug)]
enum PaymentMethod {
    CreditCard { number: String, expiry: String },
    PayPal { email: String },
    BankTransfer { account: String, routing: String },
}

#[derive(Debug)]
enum PaymentResult {
    Success(String),  // Transaction ID
    Failure(String),  // Error message
}

fn process_payment(method: PaymentMethod, amount: f64) -> PaymentResult {
    match method {
        PaymentMethod::CreditCard { number, expiry } => {
            // Simulate validation
            if number.len() == 16 {
                PaymentResult::Success(format!("CC-{}", number))
            } else {
                PaymentResult::Failure("Invalid card number".to_string())
            }
        },
        PaymentMethod::PayPal { email } => {
            // Simulate PayPal API call
            PaymentResult::Success(format!("PP-{}", email))
        },
        // BUG: Missing BankTransfer variant!
    }
}

fn main() {
    let payment = PaymentMethod::BankTransfer {
        account: "123456789".to_string(),
        routing: "987654321".to_string(),
    };

    let result = process_payment(payment, 99.99);
    println!("Payment result: {:?}", result);
}
```

### Debugging Session

**User:** "Getting panic in process_payment. Set breakpoint."

**Skill Response:**

```
🔍 Explicit debugging trigger detected
🦀 Language: Rust (detected from Cargo.toml)
🚀 Starting rust-gdb session...

⚠️ Note: Compile with debug symbols: cargo build
✅ Debugger ready
```

**Set Breakpoint:**

```
Set breakpoint at line 18
```

**Skill Response:**

```
✓ Breakpoint set at payment_processor.rs:18 (process_payment)

▶ Running...

🛑 Paused at payment_processor.rs:18
   17: fn process_payment(method: PaymentMethod, amount: f64) -> PaymentResult {
→  18:     match method {
   19:         PaymentMethod::CreditCard { number, expiry } => {
```

**Inspect Method:**

```
What's the value of method?
```

**Skill Response:**

```
Variable: method
Type: PaymentMethod
Value: PaymentMethod::BankTransfer {
    account: "123456789",
    routing: "987654321"
}

🔍 Enum variant: BankTransfer
```

**Step Through Match:**

```
Step over
```

**Skill Response:**

```
💥 PANIC! Non-exhaustive patterns

thread 'main' panicked at 'non-exhaustive patterns: `BankTransfer { .. }` not covered', payment_processor.rs:18:11

📚 Call stack:
   #0  rust_panic () at /rustc/.../panic.rs
   #1  process_payment (method=PaymentMethod::BankTransfer {...})
       at payment_processor.rs:18
   #2  main () at payment_processor.rs:39

🔍 Analysis: Match statement doesn't cover BankTransfer variant!

📋 Enum variants:
   ✓ CreditCard - covered (line 19)
   ✓ PayPal - covered (line 27)
   ✗ BankTransfer - NOT COVERED! 🐛

💡 Rust compiler should catch this... did you use #[non_exhaustive]?
```

### Solution

**Add missing match arm:**

```rust
fn process_payment(method: PaymentMethod, amount: f64) -> PaymentResult {
    match method {
        PaymentMethod::CreditCard { number, expiry } => {
            if number.len() == 16 {
                PaymentResult::Success(format!("CC-{}", number))
            } else {
                PaymentResult::Failure("Invalid card number".to_string())
            }
        },
        PaymentMethod::PayPal { email } => {
            PaymentResult::Success(format!("PP-{}", email))
        },
        PaymentMethod::BankTransfer { account, routing } => {  // ✅ Added!
            // Validate account and routing numbers
            if account.len() >= 8 && routing.len() >= 9 {
                PaymentResult::Success(format!("BT-{}-{}", account, routing))
            } else {
                PaymentResult::Failure("Invalid bank details".to_string())
            }
        },
    }
}
```

**Compiler enforcement:**

```rust
// Better: Let compiler enforce exhaustiveness
fn process_payment(method: PaymentMethod, amount: f64) -> PaymentResult {
    match method {
        PaymentMethod::CreditCard { number, expiry } => { /* ... */ },
        PaymentMethod::PayPal { email } => { /* ... */ },
        // Compiler error if this is missing:
        PaymentMethod::BankTransfer { account, routing } => { /* ... */ },
    }
}
```

## Common Patterns Across Examples

### Pattern 1: Quick Diagnosis

1. Set breakpoint at suspected location
2. Inspect variables at breakpoint
3. Identify unexpected values
4. Fix and verify

### Pattern 2: Tracing Execution

1. Set multiple breakpoints along path
2. Step through execution
3. Watch variable changes
4. Find divergence from expected behavior

### Pattern 3: Crash Investigation

1. Run until crash/panic
2. View call stack
3. Inspect state at crash point
4. Work backward to root cause

### Pattern 4: Concurrency Issues

1. Identify blocked operations
2. View all threads/goroutines
3. Inspect synchronization primitives (channels, locks)
4. Find circular dependencies

---

**Next Steps:**

- Try these examples in yer own projects
- Adapt patterns to yer specific bugs
- Learn more patterns in patterns.md
- Review API reference in reference.md
