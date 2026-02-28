"""Example usage of the Bluesky Feed Agent."""

import os
from src.bluesky_feed_agent.agent import create_agent_graph
from src.bluesky_feed_agent.states import BlueskyFeedState


def example_basic_usage():
    """Basic example of using the agent."""
    # Set your Bluesky credentials as environment variables
    os.environ["BLUESKY_USERNAME"] = "your_username"
    os.environ["BLUESKY_PASSWORD"] = "your_app_password"
    os.environ["GOOGLE_API_KEY"] = "your_google_api_key"

    # Create the agent graph
    agent = create_agent_graph()

    # Create initial state (empty handle means home feed)
    initial_state = BlueskyFeedState(user_handle="")

    # Run the agent
    result = agent.invoke(initial_state)

    # Print results
    if result.error:
        print(f"Error: {result.error}")
    else:
        print(f"Fetched {len(result.posts)} posts")
        print("\nSummary:")
        print(result.summary)


def example_user_feed():
    """Example of summarizing a specific user's feed."""
    os.environ["BLUESKY_USERNAME"] = "your_username"
    os.environ["BLUESKY_PASSWORD"] = "your_app_password"
    os.environ["GOOGLE_API_KEY"] = "your_google_api_key"

    # Create the agent graph
    agent = create_agent_graph()

    # Fetch a specific user's feed
    initial_state = BlueskyFeedState(user_handle="some.user")

    # Run the agent
    result = agent.invoke(initial_state)

    if result.error:
        print(f"Error: {result.error}")
    else:
        print(f"Summary of @some.user's feed:")
        print(result.summary)


if __name__ == "__main__":
    print("Example 1: Summarizing home feed")
    print("-" * 50)
    # example_basic_usage()

    print("\n\nExample 2: Summarizing a user's feed")
    print("-" * 50)
    # example_user_feed()

    print("\nNote: Uncomment examples and add your credentials to run")
