"""Test script to fetch information about Jan Scheffler."""

import asyncio
from apollo import ApolloClient


async def main():
    """Fetch Jan's information from Apollo."""
    print("Testing apollo-client library...\n")

    async with ApolloClient() as client:
        print("✓ Client initialized successfully\n")

        # Search for contact by email
        print("Searching for contact: jan.scheffler@qodev.ai")
        contacts = await client.search_contacts(
            q_keywords="jan.scheffler@qodev.ai",
            limit=5,
        )

        print(f"Found {len(contacts.items)} contact(s)")
        print(f"Total in Apollo: {contacts.total}\n")

        if contacts.items:
            contact = contacts.items[0]
            print("Contact Information:")
            print(f"  ID: {contact.id}")
            print(f"  Name: {contact.name}")
            print(f"  Email: {contact.email}")
            print(f"  Title: {contact.title}")
            print(f"  Company: {contact.company}")
            print(f"  LinkedIn: {contact.linkedin_url}")
            print(f"  Stage: {contact.stage}")

            if contact.phone_numbers:
                print(f"  Phone Numbers: {contact.phone_numbers}")

            # Try to get full contact details
            print(f"\nFetching full contact details...")
            full_contact = await client.get_contact(contact.id)
            print(f"  Location: {full_contact.location}")
            print(f"  Account ID: {full_contact.account_id}")
            print(f"  Created: {full_contact.created_at}")

            # Check rate limits
            print(f"\nRate Limit Status:")
            rate_limits = client.rate_limit_status
            print(f"  Hourly: {rate_limits.get('hourly_left', 0)}/{rate_limits.get('hourly_limit', 0)}")
            print(f"  Minute: {rate_limits.get('minute_left', 0)}/{rate_limits.get('minute_limit', 0)}")
            print(f"  Daily: {rate_limits.get('daily_left', 0)}/{rate_limits.get('daily_limit', 0)}")

        else:
            print("No contact found with that email in Apollo")

        # Try enrichment
        print("\n" + "="*60)
        print("Testing person enrichment...")
        try:
            person = await client.enrich_person("jan.scheffler@qodev.ai")
            print(f"✓ Enrichment successful")
            print(f"  Name: {person.get('first_name')} {person.get('last_name')}")
            print(f"  Title: {person.get('title')}")
            print(f"  Company: {person.get('organization', {}).get('name')}")
        except Exception as e:
            print(f"✗ Enrichment failed: {e}")

        print("\n✓ All tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
