"""Comprehensive test to validate all Pydantic models with real API data."""

import asyncio
from apollo import ApolloClient


async def test_contacts(client: ApolloClient):
    """Test Contact model."""
    print("\n" + "="*60)
    print("Testing Contact model...")
    try:
        result = await client.search_contacts(limit=1)
        if result.items:
            contact = result.items[0]
            print(f"✓ Contact model validated")
            print(f"  ID: {contact.id}")
            print(f"  Name: {contact.name}")
            print(f"  Email: {contact.email}")
            return True
        else:
            print("✗ No contacts found")
            return False
    except Exception as e:
        print(f"✗ Contact model error: {e}")
        return False


async def test_accounts(client: ApolloClient):
    """Test Account model."""
    print("\n" + "="*60)
    print("Testing Account model...")
    try:
        result = await client.search_accounts(limit=1)
        if result.items:
            account = result.items[0]
            print(f"✓ Account model validated")
            print(f"  ID: {account.id}")
            print(f"  Name: {account.name}")
            print(f"  Domain: {account.domain}")
            print(f"  Employees: {account.employees}")
            return True
        else:
            print("✗ No accounts found")
            return False
    except Exception as e:
        print(f"✗ Account model error: {e}")
        return False


async def test_deals(client: ApolloClient):
    """Test Deal model."""
    print("\n" + "="*60)
    print("Testing Deal model...")
    try:
        result = await client.search_deals(limit=1)
        if result.items:
            deal = result.items[0]
            print(f"✓ Deal model validated")
            print(f"  ID: {deal.id}")
            print(f"  Name: {deal.name}")
            print(f"  Amount: {deal.amount}")
            print(f"  Stage: {deal.stage}")
            return True
        else:
            print("✗ No deals found")
            return False
    except Exception as e:
        print(f"✗ Deal model error: {e}")
        return False


async def test_pipelines(client: ApolloClient):
    """Test Pipeline and Stage models."""
    print("\n" + "="*60)
    print("Testing Pipeline model...")
    try:
        result = await client.list_pipelines()
        if result.items:
            pipeline = result.items[0]
            print(f"✓ Pipeline model validated")
            print(f"  ID: {pipeline.id}")
            print(f"  Title: {pipeline.title}")
            print(f"  Is Default: {pipeline.is_default}")

            # Test stages
            print("\nTesting Stage model...")
            stages = await client.list_pipeline_stages(pipeline.id)
            if stages.items:
                stage = stages.items[0]
                print(f"✓ Stage model validated")
                print(f"  ID: {stage.id}")
                print(f"  Name: {stage.name}")
                print(f"  Probability: {stage.probability}")
                return True
            else:
                print("✗ No stages found")
                return False
        else:
            print("✗ No pipelines found")
            return False
    except Exception as e:
        print(f"✗ Pipeline/Stage model error: {e}")
        return False


async def test_notes(client: ApolloClient):
    """Test Note model."""
    print("\n" + "="*60)
    print("Testing Note model...")
    try:
        result = await client.search_notes(limit=1)
        if result.items:
            note = result.items[0]
            print(f"✓ Note model validated")
            print(f"  ID: {note.id}")
            print(f"  Title: {note.title}")
            print(f"  Content: {note.content[:50]}..." if len(note.content) > 50 else note.content)
            print(f"  Contact IDs: {len(note.contact_ids)}")
            return True
        else:
            print("✗ No notes found")
            return False
    except Exception as e:
        print(f"✗ Note model error: {e}")
        return False


async def test_calls(client: ApolloClient):
    """Test Call model."""
    print("\n" + "="*60)
    print("Testing Call model...")
    try:
        result = await client.search_calls(limit=1)
        if result.items:
            call = result.items[0]
            print(f"✓ Call model validated")
            print(f"  ID: {call.id}")
            print(f"  Contact: {call.contact_name}")
            print(f"  Status: {call.status}")
            print(f"  Duration: {call.duration}s")
            return True
        else:
            print("✗ No calls found")
            return False
    except Exception as e:
        print(f"✗ Call model error: {e}")
        return False


async def test_tasks(client: ApolloClient):
    """Test Task model."""
    print("\n" + "="*60)
    print("Testing Task model...")
    try:
        result = await client.search_tasks(limit=1)
        if result.items:
            task = result.items[0]
            print(f"✓ Task model validated")
            print(f"  ID: {task.id}")
            print(f"  Type: {task.type}")
            print(f"  Status: {task.status}")
            print(f"  Priority: {task.priority}")
            return True
        else:
            print("✗ No tasks found")
            return False
    except Exception as e:
        print(f"✗ Task model error: {e}")
        return False


async def test_emails(client: ApolloClient):
    """Test Email model."""
    print("\n" + "="*60)
    print("Testing Email model...")
    try:
        result = await client.search_emails(limit=1)
        if result.items:
            email = result.items[0]
            print(f"✓ Email model validated")
            print(f"  ID: {email.id}")
            print(f"  Contact: {email.contact_name}")
            print(f"  Subject: {email.subject}")
            print(f"  Status: {email.status}")
            return True
        else:
            print("✗ No emails found")
            return False
    except Exception as e:
        print(f"✗ Email model error: {e}")
        return False


async def test_enrichment(client: ApolloClient):
    """Test enrichment endpoints."""
    print("\n" + "="*60)
    print("Testing organization enrichment...")
    try:
        org = await client.enrich_organization("apollo.io")
        print(f"✓ Organization enrichment validated")
        print(f"  Name: {org.get('name')}")
        print(f"  Domain: {org.get('primary_domain')}")
        print(f"  Employees: {org.get('estimated_num_employees')}")
        return True
    except Exception as e:
        print(f"✗ Organization enrichment error: {e}")
        return False


async def main():
    """Run all model validation tests."""
    print("="*60)
    print("APOLLO CLIENT - COMPREHENSIVE MODEL VALIDATION")
    print("="*60)

    async with ApolloClient() as client:
        results = {}

        # Test all models
        results['Contact'] = await test_contacts(client)
        results['Account'] = await test_accounts(client)
        results['Deal'] = await test_deals(client)
        results['Pipeline/Stage'] = await test_pipelines(client)
        results['Note'] = await test_notes(client)
        results['Call'] = await test_calls(client)
        results['Task'] = await test_tasks(client)
        results['Email'] = await test_emails(client)
        results['Enrichment'] = await test_enrichment(client)

        # Summary
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)

        passed = sum(1 for v in results.values() if v)
        total = len(results)

        for model, success in results.items():
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"{status}: {model}")

        print("\n" + "="*60)
        print(f"Results: {passed}/{total} models validated successfully")
        print("="*60)

        # Final rate limit status
        rate_limits = client.rate_limit_status
        print(f"\nAPI Requests Used:")
        print(f"  Hourly: {400 - rate_limits.get('hourly_left', 0)}/400")
        print(f"  Daily: {2000 - rate_limits.get('daily_left', 0)}/2000")


if __name__ == "__main__":
    asyncio.run(main())
