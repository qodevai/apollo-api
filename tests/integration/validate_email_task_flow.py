"""Integration test for the email task creation flow.

Creates an email task draft with subject/body via the API.
Intentionally stops at draft creation to avoid sending real emails;
use send_email_task() to send programmatically.

Requires APOLLO_API_KEY environment variable. Not run in CI.
Run manually:
    APOLLO_API_KEY=... TEST_CONTACT_ID=... uv run python tests/integration/validate_email_task_flow.py
"""

import asyncio
import os
import sys

from apollo import ApolloClient


async def main() -> None:
    """Run the full email task flow."""

    if not os.getenv("APOLLO_API_KEY"):
        print("APOLLO_API_KEY not set, skipping integration test")
        sys.exit(0)

    CONTACT_ID = os.getenv("TEST_CONTACT_ID", "")
    USER_ID = os.getenv("TEST_USER_ID", "")

    if not CONTACT_ID:
        print("TEST_CONTACT_ID not set. Set it to a real contact ID.")
        sys.exit(1)

    print("=" * 60)
    print("EMAIL TASK DRAFT FLOW - INTEGRATION TEST")
    print("=" * 60)

    async with ApolloClient() as client:
        # Step 1: Create email task (status=scheduled triggers emailer_message)
        print("\nStep 1: Creating email task...")
        create_result = await client.create_email_task(
            contact_ids=[CONTACT_ID],
            note="Integration test email task",
            user_id=USER_ID or None,
            priority="medium",
        )
        task_id = create_result.id
        print(f"  Created task ID: {task_id}")
        print(f"  Type: {create_result.type}")
        print(f"  Status: {create_result.status}")
        print(f"  Emailer message: {create_result.emailer_message}")

        if not task_id:
            print("FAILED: No task ID returned")
            return

        # Step 2: Extract emailer_message ID from create result
        print("\nStep 2: Checking emailer_message...")
        if not create_result.emailer_message or not create_result.emailer_message.id:
            print("FAILED: No emailer_message created. status='scheduled' may be required.")
            return

        message_id = create_result.emailer_message.id
        print(f"  Message ID: {message_id}")
        print(f"  Message status: {create_result.emailer_message.status}")

        # Step 3: Update emailer message with subject and body
        print("\nStep 3: Setting email subject and body via update_emailer_message...")
        em_result = await client.update_emailer_message(
            message_id,
            subject="Test Subject from Integration Test",
            body_html="<p>This is a test email body.</p>",
        )
        print(f"  Subject: {em_result.subject}")
        print(f"  Body text: {(em_result.body_text or '')[:100]}")
        print(f"  Status: {em_result.status}")

        # Step 4: Verify final state
        print("\nStep 4: Verifying final state...")
        final_task = await client.get_task(task_id)
        print(f"  Task type: {final_task.type}")
        print(f"  Task status: {final_task.status}")

        # Step 5: Skip (archive) the test task to clean up
        print("\nStep 5: Skipping (archiving) test task...")
        skip_result = await client.skip_tasks([task_id])
        print(f"  Skip result: {skip_result}")

        skipped_task = await client.get_task(task_id)
        print(
            f"  After skip - status: {skipped_task.status}, skipped_at: {skipped_task.skipped_at}"
        )

        # Rate limit status
        rl = client.rate_limit_status
        print("\nRate limits after test:")
        print(f"  Hourly left: {rl.get('hourly_left', 'unknown')}")

        print("\n" + "=" * 60)
        print("INTEGRATION TEST COMPLETE")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
