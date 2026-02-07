# Example: Testing Node.js Package Changes

This example shows testing a Node.js package with uncommitted changes.

## Scenario

You're developing `myorg/ui-components` package and want to test changes with a Next.js app that uses it.

## Local Changes

```typescript
// ~/repos/ui-components/src/Button.tsx
// Added new variant prop
export interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger';  // NEW
  children: React.ReactNode;
}

export function Button({ variant = 'primary', children }: ButtonProps) {
  // ...implementation
}
```

## Setup Shadow

```bash
amplifier-shadow create \
    --local ~/repos/ui-components:myorg/ui-components \
    --name ui-test
```

## Test with Next.js App

### Method 1: Install via Git URL

```bash
amplifier-shadow exec ui-test "
    cd /workspace &&
    git clone https://github.com/myorg/next-app test-app &&
    cd test-app &&
    
    # Install ui-components from git (uses your local snapshot)
    npm install git+https://github.com/myorg/ui-components &&
    
    # Build and test
    npm run build &&
    npm test
"
```

### Method 2: Link Pre-Cloned Package

```bash
amplifier-shadow exec ui-test "
    # ui-components is already at /workspace/myorg/ui-components
    cd /workspace/myorg/ui-components &&
    npm install &&
    npm run build &&
    npm link &&
    
    # Clone app and link to local package
    cd /workspace &&
    git clone https://github.com/myorg/next-app test-app &&
    cd test-app &&
    npm install &&
    npm link @myorg/ui-components &&
    
    # Test
    npm run build &&
    npm test
"
```

## Verify Local Package Used

```bash
# Check installed version
amplifier-shadow exec ui-test "
    cd test-app &&
    npm list @myorg/ui-components
"

# Should show: @myorg/ui-components@2.0.0 -> git+https://github.com/...@abc1234
# Verify abc1234 matches your snapshot commit
```

## Test Type Safety

```bash
# If using TypeScript, verify types work
amplifier-shadow exec ui-test "
    cd test-app &&
    npm run type-check
"
```

## Expected Outcomes

### Success

```
✓ Build successful
✓ Type checking passed
✓ Tests passed (23/23)

Your new variant prop is backward compatible!
```

### Failure

```
✗ Type error: Property 'variant' does not exist on type 'ButtonProps'

Diagnosis: App's node_modules still has old version
Solution: Clear npm cache in shadow:
  amplifier-shadow exec ui-test "rm -rf /tmp/npm-cache"
```

## Cleanup

```bash
amplifier-shadow destroy ui-test
```

## Pro Tip: Watch Mode Testing

For iterative development, keep shadow running and re-run tests:

```bash
# Create shadow once
amplifier-shadow create --local ~/repos/ui-components:myorg/ui-components --name dev

# Test iteration loop
while true; do
    # Edit files on host
    
    # Recreate shadow with new snapshot
    amplifier-shadow destroy dev
    amplifier-shadow create --local ~/repos/ui-components:myorg/ui-components --name dev
    
    # Run tests
    amplifier-shadow exec dev "cd /workspace/myorg/ui-components && npm test"
    
    read -p "Continue? (y/n) " yn
    [[ $yn != "y" ]] && break
done
```
