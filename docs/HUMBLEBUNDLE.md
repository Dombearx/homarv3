# HumbleBundle Integration

The HumbleBundle integration allows Homar to check current bundles (games, books, software) available on HumbleBundle.com.

## Features

- **List all available bundles**: Get a complete list of currently active bundles
- **Get bundle details**: View detailed information about specific bundles
- **No authentication required**: Uses publicly available data

## Usage

The HumbleBundle tool is accessible through natural language commands in Discord:

### Example Commands

**Listing bundles:**
- "Show me current bundles on HumbleBundle"
- "What game bundles are available?"
- "Are there any book deals on HumbleBundle?"
- "Pokaż aktualne bundle na HumbleBundle" (Polish)

**Getting bundle details:**
- "Tell me more about the Fallout tabletop bundle"
- "What's in the Witcher bundle?"
- "Details about the programming books bundle"

## How It Works

The agent scrapes publicly available data from HumbleBundle.com using:
- **BeautifulSoup4** for HTML parsing
- **httpx** for HTTP requests
- **Regular expressions** to extract bundle information from JSON data embedded in the page

### Data Retrieved

For each bundle, the agent provides:
- Bundle name
- Category (games, books, software, or general bundle)
- Direct link to the bundle page
- Description (when getting details)
- Note about pricing tiers (pricing requires visiting the actual site)

## Technical Details

### Implementation

The HumbleBundle agent is implemented in `src/agents_as_tools/humblebundle_agent.py` and includes:

1. **list_bundles()**: Scrapes the main bundles page and returns a formatted list
2. **get_bundle_details(bundle_name)**: Fetches detailed information about a specific bundle

### Error Handling

- HTTP errors are caught and reported with user-friendly messages
- If no bundles are found, users are directed to visit the site directly
- 404 errors suggest the bundle may no longer be available

### Testing

Comprehensive unit tests are in `src/agents_as_tools/humblebundle_agent_test.py`:
- Success scenarios with mock data
- Error handling (HTTP errors, no data found)
- Bundle detail retrieval

## Dependencies

- `beautifulsoup4 ^4.12.0`: HTML parsing
- `httpx ^0.28.1`: HTTP client with async support

## Limitations

- Only shows publicly available information
- Pricing details require visiting the bundle page
- Bundle content lists may be incomplete (full details on HumbleBundle site)
- Relies on HumbleBundle's HTML structure (may break if site changes)

## Security

- No user authentication required
- No personal data collected or stored
- Only accesses public pages
- No vulnerabilities found in security scan (2 false positives in test code)

## Future Enhancements

Possible improvements:
- Cache bundle data to reduce requests
- Add filtering by price range
- Support for bundle expiration dates
- Notify when new bundles are added
