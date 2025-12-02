# Example 3: Pattern Recognition

## Scenario

User describes a problem and needs help identifying which design pattern(s) would be appropriate.

## User Query

```
User: "I have a system where multiple components need to be notified when a user's profile is updated. The number of components varies - sometimes it's just the UI, sometimes it includes logging, analytics, and email notifications. What pattern should I use?"
```

## Skill Response

This is a classic use case for the **Observer pattern**.

### Why Observer Fits Your Problem

**Pattern Match**:

- ✅ One source of change (user profile updates)
- ✅ Multiple objects need notification (UI, logging, analytics, email)
- ✅ Number of dependents varies dynamically
- ✅ Subject shouldn't know about specific dependents

**Intent**: Define a one-to-many dependency so when one object changes state, all dependents are notified automatically.

### Quick Example for Your Use Case

```python
class UserProfile:  # Subject
    def __init__(self):
        self.observers = []
        self.name = ""
        self.email = ""

    def attach(self, observer):
        self.observers.append(observer)

    def detach(self, observer):
        self.observers.remove(observer)

    def notify(self):
        for observer in self.observers:
            observer.update(self)

    def update_profile(self, name, email):
        self.name = name
        self.email = email
        self.notify()  # Notify all observers

# Observers
class UIObserver:
    def update(self, profile):
        print(f"UI updated: {profile.name}")

class LoggingObserver:
    def update(self, profile):
        print(f"Logged profile change: {profile.email}")

class AnalyticsObserver:
    def update(self, profile):
        print(f"Analytics: profile updated")

# Usage
profile = UserProfile()
profile.attach(UIObserver())
profile.attach(LoggingObserver())
profile.attach(AnalyticsObserver())

profile.update_profile("John Doe", "john@example.com")
# All three observers get notified automatically
```

### Philosophy Check

**Good fit for your use case because**:

- ✅ You have multiple (≥2) observers NOW (not "might have later")
- ✅ Observer set is dynamic (varies at runtime)
- ✅ Subject doesn't need to know about specific observers
- ✅ Clean separation of concerns

**NOT over-engineering because**:

- You explicitly said number of components varies
- You have diverse observer types (UI, logging, analytics, email)
- This is a recurring notification need, not one-off

### Alternatives Considered

**Direct Method Calls**:

```python
profile.update_profile()
ui.refresh()
logging.log_change()
analytics.track()
email.send_notification()
```

- **Pros**: Simple, explicit
- **Cons**: Tight coupling, can't add observers dynamically, violates Open/Closed
- **When to use**: If you have 1-2 fixed observers that never change

**Event Bus / Message Queue**:

- **Pros**: Complete decoupling, scalable
- **Cons**: More infrastructure, harder to debug
- **When to use**: Distributed systems, microservices

### Recommendation

**Use Observer pattern** for your use case.

**Next Steps**:

1. Define UserProfile as Subject
2. Create observer interface (update method)
3. Implement concrete observers (UI, Logging, Analytics, Email)
4. Attach observers to profile
5. Call notify() after profile updates

**Would you like**:

- Practical guide with complete implementation?
- Deep dive into Observer with push vs pull variants?
- Comparison with other notification patterns?
