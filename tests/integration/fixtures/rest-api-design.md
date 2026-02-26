---
title: Designing RESTful APIs
tags: rest,api,http
category: development
concepts: rest,api,http,endpoints,json,status-codes
---

## Resource Naming and HTTP Methods

REST APIs model resources as nouns, not verbs. Use `/users/42` instead of `/getUser?id=42`. Collection endpoints are plural (`/articles`), and individual resources are addressed by identifier (`/articles/17`). Nesting expresses ownership: `/users/42/orders` returns orders belonging to user 42, but avoid nesting deeper than two levels since `/users/42/orders/8/items/3/variants` becomes unwieldy and tightly couples the URL structure to the data model.

HTTP methods carry the semantics. GET retrieves without side effects. POST creates a new resource under a collection. PUT replaces an entire resource at a known URI. PATCH applies a partial update. DELETE removes. Using POST for everything (the "RPC over HTTP" anti-pattern) discards the cacheability and idempotency guarantees that HTTP provides for free.

Idempotency matters for reliability. GET, PUT, and DELETE are idempotent by definition: repeating the request produces the same server state. POST is not, which is why payment APIs often require a client-generated idempotency key in a header. Design your endpoints so that retrying a failed request is always safe; network failures are not exceptional in distributed systems.

For how API testing fits into automated pipelines, see [ci-pipeline-best-practices](./ci-pipeline-best-practices.md).

## Status Codes, Pagination, and Error Responses

Return the right status code. `200 OK` for successful GET/PUT/PATCH. `201 Created` for successful POST, with a `Location` header pointing to the new resource. `204 No Content` for successful DELETE. `400 Bad Request` for validation failures. `401 Unauthorized` when credentials are missing. `403 Forbidden` when credentials are valid but permissions insufficient. `404 Not Found` for missing resources. `409 Conflict` for state conflicts like duplicate keys. `422 Unprocessable Entity` when the payload is syntactically valid JSON but semantically wrong.

The [HTTP specification](https://httpwg.org/specs/rfc9110.html) defines these codes precisely. Don't return `200` with an error body; clients check status codes before parsing the response, and middleware (caches, load balancers) relies on them.

Pagination prevents unbounded responses. Cursor-based pagination (`?cursor=abc123&limit=20`) is more stable than offset-based (`?page=3&limit=20`) because inserting or deleting rows doesn't shift the window. Return pagination metadata in the response body:

```json
{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6IDQyfQ==",
    "has_more": true
  }
}
```

## Versioning and Backwards Compatibility

Version your API from day one. URL-path versioning (`/v1/users`) is explicit and easy to route at the load balancer level. Header-based versioning (`Accept: application/vnd.myapi.v2+json`) keeps URLs clean but complicates debugging since the version isn't visible in logs or browser address bars. Pick one and stay consistent.

Backwards-incompatible changes require a new version. Adding a field to a response is safe. Removing a field, renaming a field, or changing a field's type is breaking. When you must break, run both versions in parallel during a migration window and give consumers a deprecation timeline.

Error responses deserve a stable contract too. Adopt a consistent error envelope:

```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Field 'email' is required.",
    "details": [
      {"field": "email", "constraint": "required"}
    ]
  }
}
```

Machine-readable error codes (`VALIDATION_FAILED`) let clients branch on error type without parsing human-readable messages. Include a `details` array for field-level errors so forms can display inline validation feedback. See [typescript-generics](./typescript-generics.md) for typing these response structures on the client side.
