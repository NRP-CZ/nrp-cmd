#!/usr/bin/env python3
"""Comprehensive demo script for the NRP Async Client API."""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path

from nrp_cmd.async_client import get_async_client, limit_connections
from nrp_cmd.async_client.base_client import AsyncRepositoryClient
from nrp_cmd.async_client.streams import FileSink, MemorySink, MemorySource
from nrp_cmd.config import Config
from nrp_cmd.errors import (
    RepositoryClientError,
)
from nrp_cmd.types.files import File
from nrp_cmd.types.records import Record
from nrp_cmd.types.requests import Request, RequestType

# Directory for downloaded files
TMPDATA_DIR = Path("tmpdata")


async def main() -> None:
    """Main demo function."""
    print(
        """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    NRP Async Client API Demo Script                          ║
║                                                                              ║
║  This script demonstrates all documented API calls from the async_library    ║
║  documentation files. It creates test records, uploads files, manages        ║
║  requests, and performs various operations.                                  ║
║                                                                              ║
║  Downloaded files will be saved to: ./tmpdata/                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    )

    try:
        # 1. Client setup
        client = await setup_client()

        # 2-6. Records operations
        record = await create_draft_record(client)
        await read_draft_record(client, record)
        record = await update_draft_record(client, record)
        await search_draft_records(client)
        await scan_draft_records(client)

        # 7-12. Files operations
        await upload_files_to_draft(client, record)
        files = await list_files_from_draft(client, record)
        await read_file_from_draft(client, record, files)
        await download_files_from_draft(client, record, files)
        await download_files_from_draft_in_parallel(client, record, files)
        await update_file_in_draft(client, record, files)
        await delete_file_from_draft(client, record, files)

        # 13-16. Requests operations - not finished yet, thus commented!
        # request_types = await check_applicable_requests(client, record)
        # await list_requests(client)
        # request = await create_request(client, record, request_types)
        # await submit_request(client, request)

        # 17. Publish record
        published_record = await publish_record(client, record)

        # 17b. List files from published record
        await list_files_from_published(client, published_record)

        # 18. Edit record (metadata) and publish the edited draft
        edited_record = await edit_published_record(client, published_record)

        # 19. Create new version of a published record and upload a different file and publish
        new_version = await create_new_version(client, published_record)

        # 20. Record deletion (only works on drafts, so create a new draft first)
        draft_to_delete = await create_draft_record(client)
        await delete_draft_record(client, draft_to_delete)

        # 21. Complete workflow
        await complete_workflow(client)

        print_section("DEMO COMPLETED")
        print("✓ All demonstrations completed successfully!")
        print(f"✓ Downloaded files are in: {TMPDATA_DIR.absolute()}")

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()


def print_section(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_subsection(title: str) -> None:
    """Print a subsection header."""
    print(f"\n--- {title} ---\n")


async def setup_client() -> AsyncRepositoryClient:
    """Demonstrate client setup and configuration."""
    print_section("1. CLIENT SETUP AND CONFIGURATION")

    # Get client using default repository
    print_subsection("Getting client with default repository")
    try:
        client = await get_async_client(None)  # Uses default repository
        print("✓ Connected to default repository")
        print(f"  Client type: {type(client).__name__}")
    except ValueError as e:
        print(f"✗ Error: {e}")
        print("  Please configure a default repository in ~/.nrp/invenio-config.json")
        raise
    except Exception as e:
        print(f"✗ Connection error: {e}")
        raise

    # Show configuration
    print_subsection("Configuration information")
    config = Config.from_file()
    if config.default_alias:
        print(f"  Default repository alias: {config.default_alias}")
        try:
            repo = config.default_repository
            print(f"  Repository URL: {repo.url}")
        except Exception as e:
            print(f"  Could not get repository details: {e}")

    return client


async def create_draft_record(client: AsyncRepositoryClient) -> Record:
    """Demonstrate draft record creation operations."""
    print_section("2. RECORDS API - CREATING DRAFT RECORDS")

    # Basic record creation
    print_subsection("Creating a basic record")
    try:
        record = await client.records.create(
            {
                "metadata": {
                    "title": f"Demo Record - {datetime.now().isoformat()}",
                    "creators": [
                        {
                            "person_or_org": {
                                "type": "personal",
                                "family_name": "Demo",
                                "given_name": "User",
                            }
                        }
                    ],
                    "resource_type": {"id": "dataset"},
                    "publication_date": datetime.now().strftime("%Y-%m-%d"),
                }
            }
        )
        print(f"✓ Created record ID: {record.id}")
        print(f"  Title: {record.metadata.get('title', 'N/A')}")
        print(f"  Created: {record.created}")
        return record
    except RepositoryClientError as e:
        print(f"✗ Failed to create record: {e}")
        raise
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        raise


async def read_draft_record(client: AsyncRepositoryClient, record: Record) -> None:
    """Demonstrate draft record reading operations."""
    print_section("3. RECORDS API - READING DRAFT RECORDS")

    # Read by ID
    print_subsection("Reading draft record by ID")
    try:
        read_record = await client.records.draft_records.read(record.id)
        print(f"✓ Read record: {read_record.id}")
        print(f"  Title: {read_record.metadata.get('title', 'N/A')}")
        print(f"  Revision: {read_record.revision_id}")
    except Exception as e:
        print(f"✗ Failed to read record: {e}")
        raise

    # Access draft vs published
    print_subsection("Accessing draft and published records")
    try:
        draft = await client.records.draft_records.read(record.id)
        print(f"✓ Read as draft: {draft.id}")
    except Exception as e:
        print(f"✗ Could not read as draft: {e}")
        raise


async def update_draft_record(client: AsyncRepositoryClient, record: Record) -> Record:
    """Demonstrate draft record update operations."""
    print_section("4. RECORDS API - UPDATING DRAFT RECORDS")

    # Basic update
    print_subsection("Updating record metadata")
    try:
        record.metadata["title"] = f"Updated Demo Record - {datetime.now().isoformat()}"
        record.metadata["description"] = "This record was updated by the demo script"

        updated = await client.records.draft_records.update(record)
        print(f"✓ Updated record: {updated.id}")
        print(f"  New title: {updated.metadata.get('title', 'N/A')}")
        print(f"  New revision: {updated.revision_id}")
        return updated
    except Exception as e:
        print(f"✗ Failed to update record: {e}")
        raise


async def search_draft_records(client: AsyncRepositoryClient) -> None:
    """Demonstrate draft record search operations."""
    print_section("5. RECORDS API - SEARCHING RECORDS")

    # Basic search
    print_subsection("Basic search")
    try:
        results = await client.records.draft_records.search(q="demo")
        print(f"✓ Search results: {results.hits.total} total")
        print(f"  Showing {len(results.hits.hits)} records")
        for i, rec in enumerate(results.hits.hits[:3], 1):
            print(f"  {i}. {rec.metadata.get('title', 'No title')} (ID: {rec.id})")
    except Exception as e:
        print(f"✗ Search failed: {e}")
        raise

    # Search with pagination
    print_subsection("Search with pagination")
    try:
        page1 = await client.records.draft_records.search(q="", page=1, size=5)
        print(f"✓ Page 1: {len(page1.hits.hits)} records")

        if page1.links.next:
            page2 = await client.records.draft_records.next_page(record_list=page1)
            print(f"✓ Page 2: {len(page2.hits.hits)} records")
    except Exception as e:
        print(f"✗ Pagination failed: {e}")
        raise

    # Search with sorting
    print_subsection("Search with sorting")
    try:
        newest = await client.records.draft_records.search(q="", sort="newest", size=3)
        print(f"✓ Newest records: {len(newest.hits.hits)}")
        for i, rec in enumerate(newest.hits.hits, 1):
            print(f"  {i}. {rec.metadata.get('title', 'No title')}")
    except Exception as e:
        print(f"✗ Sorted search failed: {e}")
        raise


async def scan_draft_records(client: AsyncRepositoryClient) -> None:
    """Demonstrate scanning through draft records."""
    print_section("6. RECORDS API - SCANNING RECORDS")

    print_subsection("Scanning through records")
    try:
        count = 0
        async with client.records.draft_records.scan(q="demo") as records:
            async for record in records:
                count += 1
                if count <= 5:
                    print(f"  {count}. {record.metadata.get('title', 'No title')}")
                if count >= 10:  # Limit to 10 for demo
                    break
        print(f"✓ Scanned {count} records")
    except Exception as e:
        print(f"✗ Scan failed: {e}")
        raise


async def upload_files_to_draft(client: AsyncRepositoryClient, record: Record) -> None:
    """Demonstrate file upload operations to draft record."""
    print_section("7. FILES API - UPLOADING FILES")

    # Create temporary files for upload
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create test files
        test_file1 = tmpdir_path / "test_data.txt"
        test_file1.write_text("This is test data for file upload demo.")

        test_file2 = tmpdir_path / "test_data.csv"
        test_file2.write_text("column1,column2\nvalue1,value2\nvalue3,value4\n")

        # Basic upload
        print_subsection("Uploading file from string path")
        try:
            file1 = await client.files.upload(
                record,
                key="demo_data.txt",
                metadata={"description": "Demo text file"},
                source=str(test_file1),
            )
            print(f"✓ Uploaded: {file1.key} ({file1.size} bytes)")
        except Exception as e:
            print(f"✗ Upload failed: {e}")
            raise

        # Upload from Path object
        print_subsection("Uploading from Path object")
        try:
            file2 = await client.files.upload(
                record,
                key=test_file2.name,
                metadata={"description": "Demo CSV file"},
                source=test_file2,
            )
            print(f"✓ Uploaded: {file2.key} ({file2.size} bytes)")
        except Exception as e:
            print(f"✗ Upload failed: {e}")
            raise

        # Upload from memory
        print_subsection("Uploading from memory")
        try:
            data = b"This is in-memory data for the demo"
            source = MemorySource(data, content_type="text/plain")
            file3 = await client.files.upload(
                record,
                key="memory_data.txt",
                metadata={"description": "File from memory"},
                source=source,
            )
            print(f"✓ Uploaded from memory: {file3.key} ({file3.size} bytes)")
        except Exception as e:
            print(f"✗ Memory upload failed: {e}")
            raise


async def list_files_from_draft(
    client: AsyncRepositoryClient, record: Record
) -> list[File]:
    """Demonstrate file listing operations from draft record."""
    print_section("8. FILES API - LISTING FILES")

    print_subsection("Listing files on record")
    try:
        files = await client.files.list(record)
        print(f"✓ Found {len(files)} file(s)")
        for file in files:
            print(f"  - {file.key}")
            print(f"    Size: {file.size} bytes")
            print(f"    Checksum: {file.checksum}")
            print(f"    MIME type: {file.mimetype}")
            if file.metadata:
                print(f"    Metadata: {file.metadata}")
        return files
    except Exception as e:
        print(f"✗ Listing failed: {e}")
        raise


async def read_file_from_draft(
    client: AsyncRepositoryClient, record: Record, files: list[File]
) -> None:
    """Demonstrate reading file metadata from draft record."""
    print_section("9. FILES API - READING FILE METADATA")

    if not files:
        print("Skipping - no files available")
        return

    print_subsection("Reading file metadata")
    try:
        file = files[0]
        file_info = await client.files.read(record, file.key)
        print(f"✓ Read file metadata: {file_info.key}")
        print(f"  Size: {file_info.size}")
        print(f"  Checksum: {file_info.checksum}")
        print(f"  Status: {file_info.status}")
    except Exception as e:
        print(f"✗ Read failed: {e}")
        raise


async def download_files_from_draft(
    client: AsyncRepositoryClient, record: Record, files: list[File]
) -> None:
    """Demonstrate file download operations from draft record."""
    print_section("10. FILES API - DOWNLOADING FILES")

    if not files:
        print("Skipping - no files available")
        return

    # Ensure tmpdata directory exists
    TMPDATA_DIR.mkdir(exist_ok=True)

    # Download to file path
    print_subsection("Downloading files to disk")
    try:
        for file in files[:2]:  # Download first 2 files
            output_path = TMPDATA_DIR / file.key
            await client.files.download(file, FileSink(output_path))
            print(f"✓ Downloaded: {file.key} to {output_path}")
    except Exception as e:
        print(f"✗ Download failed: {e}")
        raise

    # Download to memory
    print_subsection("Downloading to memory")
    try:
        if files:
            sink = MemorySink()
            await client.files.download(files[0], sink)
            data = sink.data
            print(f"✓ Downloaded to memory: {len(data)} bytes")
    except Exception as e:
        print(f"✗ Memory download failed: {e}")
        raise


async def download_files_from_draft_in_parallel(
    client: AsyncRepositoryClient, record: Record, files: list[File]
) -> None:
    """Demonstrate parallel file download operations from draft record."""
    print_section("10. FILES API - DOWNLOADING FILES IN PARALLEL")

    if not files:
        print("Skipping - no files available")
        return

    TMPDATA_DIR.mkdir(exist_ok=True)

    print_subsection("Downloading files in parallel")

    # Limit to 5 concurrent downloads
    with limit_connections(5):
        tasks = [
            client.files.download(file_, FileSink(f"{TMPDATA_DIR}/{file_.key}"))
            for file_ in files
        ]
        results = await asyncio.gather(*tasks)

    for result in results:
        print(f"✓ Downloaded file to: {result}")


async def update_file_in_draft(
    client: AsyncRepositoryClient, record: Record, files: list[File]
) -> None:
    """Demonstrate file metadata update operations in draft record."""
    print_section("11. FILES API - UPDATING FILE METADATA")

    if not files:
        print("Skipping - no files available")
        return

    print_subsection("Updating file metadata")
    try:
        file = files[0]
        file.metadata["updated_by"] = "demo_async_api.py"
        file.metadata["updated_at"] = datetime.now().isoformat()

        updated_file = await client.files.update(file)
        print(f"✓ Updated metadata for: {updated_file.key}")
        print(f"  Metadata: {updated_file.metadata}")
    except Exception as e:
        print(f"✗ Update failed: {e}")
        raise


async def delete_file_from_draft(
    client: AsyncRepositoryClient, record: Record, files: list[File]
) -> None:
    """Demonstrate file deletion operations from draft record."""
    print_section("12. FILES API - DELETING FILES")

    # Only delete if we have more than 1 file, to keep at least one
    if len(files) > 1:
        print_subsection("Deleting a file")
        try:
            file_to_delete = files[-1]  # Delete the last file
            await client.files.delete(file_to_delete)
            print(f"✓ Deleted file: {file_to_delete.key}")
        except Exception as e:
            print(f"✗ Delete failed: {e}")
            raise
    else:
        print("Skipping deletion - keeping at least one file on record")


async def check_applicable_requests(
    client: AsyncRepositoryClient, record: Record
) -> list[RequestType]:
    """Demonstrate checking applicable requests."""
    print_section("13. REQUESTS API - APPLICABLE REQUESTS")

    print_subsection("Checking available request types")
    try:
        request_types = await client.requests.applicable_requests(record)
        print(f"✓ Found {len(request_types.hits)} applicable request type(s)")
        for req_type in request_types.hits:
            print(f"  - Type: {req_type.type_id}")
            print(f"    Name: {req_type.name}")
            if hasattr(req_type, "description") and req_type.description:
                print(f"    Description: {req_type.description}")
        return request_types.hits
    except Exception as e:
        print(f"✗ Failed to get applicable requests: {e}")
        raise


async def list_requests(client: AsyncRepositoryClient) -> None:
    """Demonstrate listing requests."""
    print_section("14. REQUESTS API - LISTING REQUESTS")

    # List all requests
    print_subsection("Listing all accessible requests")
    try:
        all_requests = await client.requests.all()
        print(f"✓ Total requests: {all_requests.hits.total}")
        for i, req in enumerate(all_requests.hits.hits[:5], 1):
            print(f"  {i}. {req.type} - Status: {req.status}")
            if hasattr(req, "title") and req.title:
                print(f"     Title: {req.title}")
    except Exception as e:
        print(f"✗ Listing failed: {e}")
        raise

    # List by status
    print_subsection("Listing requests by status")
    try:
        submitted = await client.requests.submitted()
        print(f"✓ Submitted requests: {submitted.hits.total}")

        accepted = await client.requests.accepted()
        print(f"✓ Accepted requests: {accepted.hits.total}")
    except Exception as e:
        print(f"✗ Status filtering failed: {e}")
        raise


async def create_request(
    client: AsyncRepositoryClient,
    record: Record,
    request_types: list[RequestType],
) -> Request | None:
    """Demonstrate creating and managing requests."""
    print_section("15. REQUESTS API - CREATING REQUESTS")

    if not request_types:
        print("Skipping - no request types available")
        return None

    # Try to find a publish request type
    publish_type = None
    for rt in request_types:
        if "publish" in rt.type_id.lower():
            publish_type = rt
            break

    if not publish_type:
        print("No publish request type available")
        return None

    print_subsection(f"Creating {publish_type.type_id} request")
    try:
        request = await client.requests.create(
            publish_type,
            payload={"message": "Request created by demo script"},
            submit=False,  # Create but don't submit yet
        )
        print(f"✓ Created request: {request.id}")
        print(f"  Type: {request.type}")
        print(f"  Status: {request.status}")
        return request
    except Exception as e:
        print(f"✗ Request creation failed: {e}")
        raise


async def submit_request(
    client: AsyncRepositoryClient, request: Request | None
) -> None:
    """Demonstrate submitting a request."""
    print_section("16. REQUESTS API - SUBMITTING REQUESTS")

    if not request:
        print("Skipping - no request available")
        return

    # Only submit if it's in created status
    if request.status == "created":
        print_subsection("Submitting request")
        try:
            submitted = await client.requests.submit(
                request, payload={"message": "Submitting for review"}
            )
            print(f"✓ Submitted request: {submitted.id}")
            print(f"  Status: {submitted.status}")
        except Exception as e:
            print(f"✗ Submission failed: {e}")
            raise
    else:
        print(f"Request is in '{request.status}' status, cannot submit")


async def list_files_from_published(
    client: AsyncRepositoryClient, record: Record
) -> None:
    """Demonstrate listing files from a published record."""
    print_section("17b. FILES API - LISTING FILES FROM PUBLISHED RECORD")

    print_subsection("Listing files from published record")
    try:
        # List files from published record
        files = await client.files.list(record)
        print(f"✓ Found {len(files)} file(s) in published record")
        for file in files:
            print(f"  - {file.key} ({file.size} bytes)")
            print(f"    Checksum: {file.checksum}")
            print(f"    Download URL: {file.links.content}")
    except Exception as e:
        print(f"✗ Failed to list files from published record: {e}")
        raise


async def publish_record(client: AsyncRepositoryClient, record: Record) -> Record:
    """Demonstrate publishing a draft record."""
    print_section("17. RECORDS API - PUBLISHING RECORDS")

    print_subsection("Publishing draft record")
    try:
        result = await client.records.publish(record)

        # Check if result is a Request or a Record
        if isinstance(result, Request):
            print(f"✓ Publish request created: {result.id}")
            print(f"  Type: {result.type}")
            print(f"  Status: {result.status}")
            print("  Note: Publishing requires approval workflow")
            # For demo purposes, we'll assume the request gets approved
            # In real scenarios, you'd wait for curator approval
            raise Exception(
                "Publishing requires approval - cannot continue demo automatically"
            )
        else:
            # It's a Record - published immediately
            print(f"✓ Published record: {result.id}")
            print(f"  Title: {result.metadata.get('title', 'N/A')}")
            if hasattr(result.links, "self_html"):
                print(f"  Public URL: {result.links.self_html}")
            return result
    except Exception as e:
        print(f"✗ Publish failed: {e}")
        raise


async def edit_published_record(
    client: AsyncRepositoryClient, record: Record
) -> Record:
    """Demonstrate editing a published record's metadata."""
    print_section("18. RECORDS API - EDITING PUBLISHED RECORDS")

    print_subsection("Requesting to edit published record")
    try:
        result = await client.records.edit_metadata(record)

        # Check if result is a Request or a Record (draft)
        if isinstance(result, Request):
            print(f"✓ Edit request created: {result.id}")
            print(f"  Type: {result.type}")
            print(f"  Status: {result.status}")
            print("  Note: Editing requires approval workflow")
            raise Exception(
                "Editing requires approval - cannot continue demo automatically"
            )
        else:
            # It's a Record (draft) - can edit immediately
            print(f"✓ Draft created for editing: {result.id}")
            print(f"  Original title: {result.metadata.get('title', 'N/A')}")

            # Update the metadata
            print_subsection("Updating draft metadata")
            result.metadata["title"] = (
                f"{result.metadata.get('title', 'Demo')} - Edited"
            )
            result.metadata["description"] = (
                "This record was edited via the demo script"
            )

            updated_draft = await client.records.update(result)
            print(f"✓ Updated draft: {updated_draft.id}")
            print(f"  New title: {updated_draft.metadata.get('title', 'N/A')}")

            # Publish the edited draft
            print_subsection("Publishing edited draft")
            published = await client.records.publish(updated_draft)

            if isinstance(published, Request):
                print(f"✓ Publish request created: {published.id}")
                print("  Note: Publishing edited record requires approval")
                raise Exception(
                    "Publishing requires approval - cannot continue demo automatically"
                )
            else:
                print(f"✓ Published edited record: {published.id}")
                print(f"  Title: {published.metadata.get('title', 'N/A')}")
                return published
    except Exception as e:
        print(f"✗ Edit operation failed: {e}")
        raise


async def create_new_version(client: AsyncRepositoryClient, record: Record) -> Record:
    """Demonstrate creating a new version of a published record."""
    print_section("19. RECORDS API - CREATING NEW VERSION")

    print_subsection("Creating new version of published record")
    try:
        result = await client.records.new_version(record)

        # Check if result is a Request or a Record (draft)
        if isinstance(result, Request):
            print(f"✓ New version request created: {result.id}")
            print(f"  Type: {result.type}")
            print(f"  Status: {result.status}")
            print("  Note: Creating new version requires approval")
            raise Exception(
                "New version requires approval - cannot continue demo automatically"
            )
        else:
            # It's a Record (draft of new version)
            print(f"✓ New version draft created: {result.id}")
            print(f"  Title: {result.metadata.get('title', 'N/A')}")

            # Update metadata for new version
            print_subsection("Updating new version metadata")
            result.metadata["title"] = (
                f"{result.metadata.get('title', 'Demo')} - Version 2"
            )
            result.metadata["version"] = "2.0"

            updated_draft = await client.records.update(result)
            print(f"✓ Updated new version draft: {updated_draft.id}")
            print(f"  Title: {updated_draft.metadata.get('title', 'N/A')}")

            # Upload a different file to the new version
            print_subsection("Uploading file to new version")
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                version_file = tmpdir_path / "version2_data.txt"
                version_file.write_text("This is data for version 2 of the record")

                file = await client.files.upload(
                    updated_draft,
                    key="version2_data.txt",
                    metadata={"description": "Version 2 data file"},
                    source=version_file,
                )
                print(f"✓ Uploaded: {file.key} ({file.size} bytes)")

            # Publish the new version
            print_subsection("Publishing new version")
            published = await client.records.publish(updated_draft)

            if isinstance(published, Request):
                print(f"✓ Publish request created: {published.id}")
                print("  Note: Publishing new version requires approval")
                raise Exception(
                    "Publishing requires approval - cannot continue demo automatically"
                )
            else:
                print(f"✓ Published new version: {published.id}")
                print(f"  Title: {published.metadata.get('title', 'N/A')}")
                if hasattr(published.links, "self_html"):
                    print(f"  Public URL: {published.links.self_html}")
                return published
    except Exception as e:
        print(f"✗ New version creation failed: {e}")
        raise


async def delete_draft_record(client: AsyncRepositoryClient, record: Record) -> None:
    """Demonstrate draft record deletion."""
    print_section("20. RECORDS API - DELETING RECORDS")

    print_subsection("Deleting record")
    try:
        await client.records.draft_records.delete(record.id)
        print(f"✓ Deleted record: {record.id}")
    except Exception as e:
        print(f"✗ Delete failed: {e}")
        raise


async def complete_workflow(client: AsyncRepositoryClient) -> None:
    """Demonstrate a complete workflow."""
    print_section("23. COMPLETE WORKFLOW - CREATE, UPLOAD, AND MANAGE")

    try:
        # Create record
        print_subsection("Step 1: Create record")
        record = await client.records.create(
            {
                "metadata": {
                    "title": f"Complete Workflow Demo - {datetime.now().isoformat()}",
                    "creators": [
                        {
                            "person_or_org": {
                                "type": "personal",
                                "family_name": "Workflow",
                                "given_name": "Demo",
                            }
                        }
                    ],
                    "resource_type": {"id": "dataset"},
                    "publication_date": datetime.now().strftime("%Y-%m-%d"),
                }
            }
        )
        print(f"✓ Created: {record.id}")

        # Upload files
        print_subsection("Step 2: Upload files")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create and upload data file
            data_file = tmpdir_path / "workflow_data.txt"
            data_file.write_text("Complete workflow demonstration data")

            file = await client.files.upload(
                record,
                key="workflow_data.txt",
                metadata={"description": "Workflow demo data"},
                source=data_file,
            )
            print(f"✓ Uploaded: {file.key}")

        # List files
        print_subsection("Step 3: List files")
        files = await client.files.list(record)
        print(f"✓ Found {len(files)} file(s)")

        # Update metadata
        print_subsection("Step 4: Update record metadata")
        record.metadata["description"] = "This record demonstrates a complete workflow"
        updated = await client.records.update(record)
        print(f"✓ Updated: {updated.id}")

        # Download file
        print_subsection("Step 5: Download file")
        TMPDATA_DIR.mkdir(exist_ok=True)
        if files:
            output_path = TMPDATA_DIR / files[0].key
            await client.files.download(files[0], FileSink(output_path))
            print(f"✓ Downloaded to: {output_path}")

        # Check requests - not fully implemented yet
        # print_subsection("Step 6: Check applicable requests")
        # request_types = await client.requests.applicable_requests(record)
        # print(f"✓ Found {len(request_types.hits)} applicable request type(s)")

        # Clean up
        print_subsection("Step 7: Clean up")
        await client.records.draft_records.delete(record.id)
        print(f"✓ Deleted record: {record.id}")

        print("\n✓ Complete workflow finished successfully!")

    except Exception as e:
        print(f"✗ Workflow failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
