# OAuth2 Helpers Implementation

## Purpose

The `helpers/` directory provides utility classes and functions that support OAuth2 flow implementation. Currently, it contains the `ConditionChain` executor which orchestrates the execution of multiple `Condition` objects in sequence.

## Architecture Context

```
OAuth2 Flows
       ↓
   Preconditions
       ↓
┌──────────────────────────────────────┐
│        OAUTH2 HELPERS LAYER          │
│  ┌────────────────────────────────┐  │
│  │ ConditionChain                 │  │
│  │  - Execute conditions in order │  │
│  │  - Short-circuit on failure    │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
       ↓
   Individual Conditions
```

## Key Files & Logic

### `condition_executor.py` (37 lines)
Implements the `ConditionChain` class for executing sequences of `Condition` objects.

---

## ConditionChain

### Purpose
Executes a sequence of `Condition` objects in order, stopping at the first failure.

### Structure
```python
class ConditionChain:
    """
    Executes a sequence of Conditions in order.
    Stops at the first FailedResult.
    """
    
    def __init__(self, conditions: Sequence[Condition]):
        self._conditions = list(conditions)
    
    async def execute(
        self,
        *,
        context: Mapping[str, Any],
        ray_id: str,
    ) -> Result:
        for condition in self._conditions:
            result = await condition.validate(
                context=context,
                ray_id=ray_id,
            )
            
            # Business failure → short-circuit
            if result.status is False:
                return result
        
        # All conditions passed
        return SuccessResult(
            ray_id=ray_id,
            client_message=None,
        )
```

### Behavior
1. **Sequential Execution**: Conditions are executed in the order they were provided
2. **Short-Circuit on Failure**: Stops at the first `FailedResult`
3. **Success if All Pass**: Returns `SuccessResult` if all conditions pass

---

## Usage Examples

### Basic Usage
```python
from q_scope.implementations.oauth2.helpers import ConditionChain
from q_scope.implementations.oauth2.templates.base import Condition

# Define conditions
chain = ConditionChain([
    ValidateRefreshTokenPresenceCondition(),
    AuthenticateClientCondition(),
    ValidateRefreshTokenCondition(),
    CheckTokenLimitCondition()
])

# Execute
result = await chain.execute(context=context, ray_id=ray_id)

if result.status:
    # All conditions passed
    print("Validation successful")
else:
    # A condition failed
    print(f"Validation failed: {result.error_code} - {result.client_message}")
```

### In OAuth Flow Preconditions
```python
class RefreshTokenFlow(OAuth2Authorization):
    async def _preconditions(self, context, ray_id):
        chain = ConditionChain([
            ValidateRefreshTokenPresenceCondition(),
            AuthenticateClientCondition(),
            ValidateRefreshTokenCondition(),
            CheckTokenLimitCondition()
        ])
        
        result = await chain.execute(context=context, ray_id=ray_id)
        
        if not result.status:
            # Raise OAuth error to stop flow execution
            raise OAuthError(result.error_code, result.client_message)
```

### Dynamic Condition Building
```python
def build_refresh_token_conditions(config):
    conditions = [
        ValidateRefreshTokenPresenceCondition(),
        AuthenticateClientCondition(),
        ValidateRefreshTokenCondition()
    ]
    
    # Conditionally add token limit check
    if config.max_active_access_tokens is not None:
        conditions.append(CheckTokenLimitCondition())
    
    return ConditionChain(conditions)

# Usage
chain = build_refresh_token_conditions(config)
result = await chain.execute(context=context, ray_id=ray_id)
```

---

## Design Patterns

### 1. Chain of Responsibility
Each `Condition` in the chain has the opportunity to validate and either:
- **Pass**: Return `SuccessResult` and let the next condition run
- **Fail**: Return `FailedResult` and stop the chain

### 2. Composite Pattern
`ConditionChain` treats a collection of `Condition` objects as a single unit, providing a uniform interface for validation.

### 3. Fail-Fast
The chain stops at the first failure, avoiding unnecessary computation and providing immediate feedback.

---

## Advantages

### 1. Composability
Build complex validation logic from simple, reusable conditions:
```python
# Reusable conditions
auth_conditions = [
    AuthenticateClientCondition(),
    ValidateClientEnabledCondition()
]

# Compose into different flows
auth_code_chain = ConditionChain(auth_conditions + [ValidateAuthCodeCondition()])
refresh_token_chain = ConditionChain(auth_conditions + [ValidateRefreshTokenCondition()])
```

### 2. Testability
Test conditions in isolation:
```python
async def test_validate_refresh_token_condition():
    condition = ValidateRefreshTokenCondition()
    
    # Test with valid token
    context = {"refresh_token": "valid_token"}
    result = await condition.validate(context=context, ray_id="test")
    assert result.status is True
    
    # Test with missing token
    context = {}
    result = await condition.validate(context=context, ray_id="test")
    assert result.status is False
    assert result.error_code == OAuthErrors.INVALID_REQUEST
```

### 3. Readability
Flow preconditions are explicit and self-documenting:
```python
chain = ConditionChain([
    ValidateRefreshTokenPresenceCondition(),  # Step 1: Check token exists
    AuthenticateClientCondition(),            # Step 2: Verify client
    ValidateRefreshTokenCondition(),          # Step 3: Validate token
    CheckTokenLimitCondition()                # Step 4: Enforce limits
])
```

### 4. Flexibility
Easy to add, remove, or reorder conditions without changing flow logic:
```python
# Add new condition
chain = ConditionChain([
    ValidateRefreshTokenPresenceCondition(),
    AuthenticateClientCondition(),
    ValidateClientScopesCondition(),  # New condition
    ValidateRefreshTokenCondition(),
    CheckTokenLimitCondition()
])
```

---

## Extension Guidelines

### Creating a New Condition

1. **Implement Condition Interface**:
   ```python
   from q_scope.implementations.oauth2.templates.base import Condition
   from q_scope.implementations.datastrutures import SuccessResult, FailedResult
   
   class ValidateNewThingCondition(Condition):
       async def validate(self, *, context, ray_id) -> Result:
           new_thing = context.get("new_thing")
           
           if new_thing is None:
               return FailedResult(
                   ray_id=ray_id,
                   client_message="new_thing is required",
                   error_code="INVALID_REQUEST"
               )
           
           # Validation logic
           if not self._is_valid(new_thing):
               return FailedResult(
                   ray_id=ray_id,
                   client_message="new_thing is invalid",
                   error_code="INVALID_REQUEST"
               )
           
           return SuccessResult(ray_id=ray_id, client_message=None)
       
       def _is_valid(self, new_thing):
           # Validation logic
           return True
   ```

2. **Add to Chain**:
   ```python
   chain = ConditionChain([
       ValidateNewThingCondition(),
       # ... other conditions
   ])
   ```

### Creating a Custom Chain Executor

If you need different execution logic (e.g., parallel execution, retry logic):

```python
class ParallelConditionChain:
    """Execute conditions in parallel and aggregate results."""
    
    def __init__(self, conditions):
        self._conditions = list(conditions)
    
    async def execute(self, *, context, ray_id) -> Result:
        import asyncio
        
        # Execute all conditions in parallel
        results = await asyncio.gather(*[
            condition.validate(context=context, ray_id=ray_id)
            for condition in self._conditions
        ])
        
        # Check if any failed
        for result in results:
            if not result.status:
                return result
        
        return SuccessResult(ray_id=ray_id, client_message=None)
```

---

## Dependencies

### Internal
- **templates/base**: `Condition`
- **datastrutures**: `Result`, `SuccessResult`, `FailedResult`

### External
- **typing**: `Sequence`, `Mapping`, `Any`

---

## Testing Strategy

### Unit Tests
- Test chain execution order
- Test short-circuit behavior
- Test success when all conditions pass
- Test failure propagation

### Integration Tests
- Test chain with real conditions
- Test chain in OAuth flow preconditions

---

## Related Documentation

- **OAuth2 Layer**: [../imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/imp.md)
- **Templates**: [../templates/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/templates/imp.md)
- **OAuth Flows**: [../oauth_flows/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/oauth_flows/imp.md)

---

**Summary**: The OAuth2 helpers layer provides the `ConditionChain` executor for orchestrating sequential validation logic. It implements the Chain of Responsibility pattern, enabling composable, testable, and readable validation logic for OAuth2 flows.
