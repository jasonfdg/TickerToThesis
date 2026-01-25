# Ghost Newsletter API - Email Sending via Admin API

## The Problem

Ghost's Admin API does not send newsletter emails when you include `newsletter` or `email_segment` in the POST body. The API silently ignores these parameters.

**This doesn't work:**
```python
# WRONG - newsletter parameter is ignored
payload = {
    "posts": [{
        "title": "My Post",
        "html": "<p>Content</p>",
        "status": "published",
        "newsletter": "default-newsletter",  # IGNORED
        "email_segment": "all",              # IGNORED
    }]
}
response = requests.post("/ghost/api/admin/posts/", json=payload)
# Result: Post is published but NO email is sent
```

## The Solution: Two-Step Approach with Query Parameters

Ghost requires the newsletter to be passed as a **query parameter** when transitioning a post from draft to published.

### Step 1: Create Post as Draft
```python
payload = {
    "posts": [{
        "title": "My Post",
        "html": "<p>Content</p>",
        "status": "draft",  # Must be draft first
    }]
}
response = requests.post("/ghost/api/admin/posts/", json=payload)
post_id = response.json()["posts"][0]["id"]
updated_at = response.json()["posts"][0]["updated_at"]
```

### Step 2: Publish with Newsletter Query Parameters
```python
# Newsletter and email_segment as QUERY PARAMETERS
url = f"/ghost/api/admin/posts/{post_id}/?newsletter=default-newsletter&email_segment=all"

payload = {
    "posts": [{
        "updated_at": updated_at,
        "status": "published",
    }]
}
response = requests.put(url, json=payload)

# Result: Post is published AND email is sent!
email_status = response.json()["posts"][0]["email"]
# {"status": "pending", "email_count": 4, ...}
```

## Query Parameters

| Parameter | Values | Description |
|-----------|--------|-------------|
| `newsletter` | Newsletter slug (e.g., `default-newsletter`) | Required to trigger email |
| `email_segment` | `all`, `status:free`, `status:-free` | Who receives the email |

### Email Segment Options
- `all` - All subscribers (free + paid)
- `status:free` - Free subscribers only
- `status:-free` - Paid subscribers only (note the minus sign)

## Complete Python Example

```python
import aiohttp
import json

async def publish_post_with_email(
    title: str,
    html: str,
    newsletter_slug: str = "default-newsletter",
    email_segment: str = "all",
):
    """Publish a post and send newsletter email using Ghost Admin API."""

    base_url = "https://your-site.ghost.io"
    headers = {
        "Authorization": f"Ghost {jwt_token}",
        "Content-Type": "application/json",
        "Accept-Version": "v5.0",
    }

    async with aiohttp.ClientSession() as session:
        # Step 1: Create as draft
        url = f"{base_url}/ghost/api/admin/posts/"
        payload = {
            "posts": [{
                "title": title,
                "html": html,
                "status": "draft",
            }]
        }

        async with session.post(url, headers=headers, json=payload) as response:
            result = await response.json()
            post = result["posts"][0]
            post_id = post["id"]
            updated_at = post["updated_at"]

        # Step 2: Publish with newsletter query params
        url = f"{base_url}/ghost/api/admin/posts/{post_id}/?newsletter={newsletter_slug}&email_segment={email_segment}"
        payload = {
            "posts": [{
                "updated_at": updated_at,
                "status": "published",
            }]
        }

        async with session.put(url, headers=headers, json=payload) as response:
            result = await response.json()
            post = result["posts"][0]

            # Check email status
            email = post.get("email")
            if email:
                print(f"Email queued: {email['status']}")
                print(f"Recipients: {email['email_count']}")

            return post
```

## Sending Email for Existing Posts

For posts that are already published without email, use the same two-step approach:

```python
async def send_email_for_existing_post(post_id: str):
    """Send email for an already-published post."""

    # Step 1: Get current post and unpublish to draft
    post = await get_post(post_id)
    updated_at = post["updated_at"]

    await update_post(post_id, updated_at, status="draft")

    # Step 2: Re-publish with newsletter query params
    url = f"/posts/{post_id}/?newsletter=default-newsletter&email_segment=all"
    # ... same as above
```

## Requirements

### Ghost Plan
- **Starter** ($15/mo): Content API only - NO email via API
- **Publisher** ($29/mo): Full Admin API - Email via API works
- **Business/Custom**: Full Admin API - Email via API works

### Integration Permissions
After upgrading your Ghost plan, you may need to:
1. Delete the existing custom integration
2. Create a new integration to get fresh permissions
3. Use the new Admin API key

## Common Errors

### 403 Forbidden on /emails/ endpoint
```
{"message": "API tokens do not have permission to access this endpoint"}
```
**Solution**: Create a new integration after upgrading to Publisher plan.

### Newsletter parameter ignored
```python
# Response shows newsletter: None even though you passed it
```
**Solution**: Use the two-step approach with query parameters (not body).

### 406 Not Acceptable
```
{"message": "Request could not be served, the endpoint was not found."}
```
**Solution**: Update `Accept-Version` header to match your Ghost version.

## TTT Pipeline Integration

### CLI Usage
```bash
# Publish memo and send email
python newsletter_publisher.py publish --ticker COIN --publish --send-email

# Send email for existing post
python newsletter_publisher.py send-email --post-id abc123

# Full pipeline
python TickerToThesis.py AAPL "thesis..." --publish --send-email
```

### Code Flow
```
TickerToThesis.py --publish --send-email
    │
    ▼
newsletter_publisher.publish_memo(ticker, send_email=True)
    │
    ▼
GhostClient.publish_post(send_email=True)
    │
    ├── Step 1: create_post(status="draft")
    │
    └── Step 2: PUT /posts/{id}/?newsletter=default-newsletter&email_segment=all
                with status="published"
    │
    ▼
Email sent to subscribers!
```

## References

- [Ghost Admin API Docs](https://ghost.org/docs/admin-api/)
- [Ghost Forum: Create post and send via email](https://forum.ghost.org/t/create-post-and-send-via-email-using-admin-api/35529)
- [Ghost Forum: Posts API & Newsletters](https://forum.ghost.org/t/ghost-posts-api-newsletters/30824)

---

*Last updated: 2026-01-25*
*Discovered during TTT Newsletter Platform integration*
