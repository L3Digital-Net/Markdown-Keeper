---
title: TypeScript Generics and Advanced Type Patterns
tags: typescript,types,generics
category: development
concepts: typescript,generics,type,interface,constraints
---

## Generic Functions and Constraints

Generics let you write functions and classes that work across types without losing type information. A function that accepts `any` and returns `any` compiles, but the caller loses all inference. Generics preserve the relationship between inputs and outputs.

```typescript
function first<T>(items: T[]): T | undefined {
  return items[0];
}

const n = first([1, 2, 3]);    // inferred as number | undefined
const s = first(["a", "b"]);   // inferred as string | undefined
```

Constraints narrow what a generic type can be. Use `extends` to require specific structure:

```typescript
function getLength<T extends { length: number }>(item: T): number {
  return item.length;
}

getLength("hello");      // OK, string has .length
getLength([1, 2]);       // OK, array has .length
getLength(42);           // Error: number has no .length
```

Without the constraint, accessing `.length` inside the function body would be a type error because `T` could be anything. Constraints also work with interfaces and union types. A common pattern is `T extends string | number` for functions that accept primitives but not objects.

Multiple type parameters express relationships between arguments. A `merge<A, B>(a: A, b: B): A & B` signature tells the compiler the return type is the intersection of both inputs, which preserves all properties from both objects in the inferred result.

## Conditional Types and Utility Types

Conditional types let you express type-level branching. The syntax mirrors the ternary operator: `T extends U ? X : Y`. The standard library's `Extract` and `Exclude` utility types are built on this pattern.

```typescript
type IsString<T> = T extends string ? true : false;

type A = IsString<"hello">;  // true
type B = IsString<42>;       // false
```

When `T` is a union, conditional types distribute over each member. `Exclude<"a" | "b" | "c", "a">` evaluates to `"b" | "c"` because the condition is applied to each union member independently. This distribution behavior is what makes utility types like `NonNullable<T>` (which is `Exclude<T, null | undefined>`) work correctly.

The `infer` keyword extracts types from within a conditional. For example, extracting the return type of a function:

```typescript
type ReturnOf<T> = T extends (...args: any[]) => infer R ? R : never;
type X = ReturnOf<() => string>;  // string
```

The built-in `ReturnType<T>` utility does exactly this. Other essential utilities: `Partial<T>` makes all properties optional, `Required<T>` does the inverse, `Pick<T, K>` selects a subset of keys, and `Omit<T, K>` excludes keys. Refer to the [TypeScript handbook on utility types](https://www.typescriptlang.org/docs/handbook/utility-types.html) for the full list.

## Mapped Types and Real-World Patterns

Mapped types iterate over keys to produce new types. `Partial<T>` is implemented as:

```typescript
type Partial<T> = {
  [K in keyof T]?: T[K];
};
```

The `in keyof` syntax loops over each property, and the `?` modifier makes it optional. You can also use `-?` to remove optionality or add `readonly` / `-readonly` modifiers. This mechanism is how `Required<T>` and `Readonly<T>` are defined.

Template literal types combine mapped types with string manipulation for typed event systems, API route definitions, or CSS property builders:

```typescript
type EventName<T extends string> = `on${Capitalize<T>}`;
type ClickEvent = EventName<"click">;  // "onClick"
```

A practical pattern for API clients: define a response wrapper generic that enforces consistent structure across all endpoints.

```typescript
interface ApiResponse<T> {
  data: T;
  meta: { timestamp: string; requestId: string };
}

interface User { id: number; name: string; }
type UserResponse = ApiResponse<User>;
```

This pairs well with the error envelope pattern described in [rest-api-design](./rest-api-design.md). By making the success and error shapes generic, client code can narrow the response type based on status code checks, giving full type safety from the network boundary through to the UI layer.
