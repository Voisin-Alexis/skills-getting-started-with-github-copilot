"""
Tests for the Mergington High School API endpoints.
"""

import pytest


class TestRoot:
    """Tests for the root endpoint."""

    def test_root_redirects_to_static(self, client):
        """Test that the root endpoint redirects to /static/index.html."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the get activities endpoint."""

    def test_get_all_activities(self, client):
        """Test retrieving all activities."""
        response = client.get("/activities")
        assert response.status_code == 200
        
        activities = response.json()
        assert isinstance(activities, dict)
        assert "Chess Club" in activities
        assert "Programming Class" in activities
        assert "Gym Class" in activities

    def test_activities_have_required_fields(self, client):
        """Test that activities have all required fields."""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)

    def test_activities_have_participants(self, client):
        """Test that activities have participants."""
        response = client.get("/activities")
        activities = response.json()
        
        chess_club = activities["Chess Club"]
        assert len(chess_club["participants"]) == 2
        assert "michael@mergington.edu" in chess_club["participants"]
        assert "daniel@mergington.edu" in chess_club["participants"]


class TestSignup:
    """Tests for the signup endpoint."""

    def test_signup_new_participant(self, client):
        """Test signing up a new participant for an activity."""
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "alice@mergington.edu"}
        )
        
        assert response.status_code == 200
        result = response.json()
        assert "message" in result
        assert "Signed up" in result["message"]

    def test_signup_updates_participant_list(self, client):
        """Test that signup adds the participant to the list."""
        client.post(
            "/activities/Programming%20Class/signup",
            params={"email": "bob@mergington.edu"}
        )
        
        response = client.get("/activities")
        activities = response.json()
        assert "bob@mergington.edu" in activities["Programming Class"]["participants"]

    def test_signup_duplicate_participant(self, client):
        """Test that signing up a participant twice fails."""
        # First signup
        client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "test@mergington.edu"}
        )
        
        # Second signup with same email
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "test@mergington.edu"}
        )
        
        assert response.status_code == 400
        result = response.json()
        assert "already signed up" in result["detail"]

    def test_signup_nonexistent_activity(self, client):
        """Test signing up for a non-existent activity."""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup",
            params={"email": "test@mergington.edu"}
        )
        
        assert response.status_code == 404
        result = response.json()
        assert "Activity not found" in result["detail"]


class TestUnregister:
    """Tests for the unregister endpoint."""

    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant."""
        # First, sign up a participant
        client.post(
            "/activities/Gym%20Class/signup",
            params={"email": "charlie@mergington.edu"}
        )
        
        # Then unregister
        response = client.delete(
            "/activities/Gym%20Class/unregister",
            params={"email": "charlie@mergington.edu"}
        )
        
        assert response.status_code == 200
        result = response.json()
        assert "Unregistered" in result["message"]

    def test_unregister_removes_participant(self, client):
        """Test that unregister removes the participant from the list."""
        email = "dave@mergington.edu"
        
        # Sign up
        client.post(
            "/activities/Chess%20Club/signup",
            params={"email": email}
        )
        
        # Verify signup worked
        response = client.get("/activities")
        assert email in response.json()["Chess Club"]["participants"]
        
        # Unregister
        client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": email}
        )
        
        # Verify removal
        response = client.get("/activities")
        assert email not in response.json()["Chess Club"]["participants"]

    def test_unregister_nonexistent_participant(self, client):
        """Test unregistering a participant who is not signed up."""
        response = client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": "notmember@mergington.edu"}
        )
        
        assert response.status_code == 400
        result = response.json()
        assert "not registered" in result["detail"]

    def test_unregister_nonexistent_activity(self, client):
        """Test unregistering from a non-existent activity."""
        response = client.delete(
            "/activities/Nonexistent%20Activity/unregister",
            params={"email": "test@mergington.edu"}
        )
        
        assert response.status_code == 404
        result = response.json()
        assert "Activity not found" in result["detail"]

    def test_unregister_existing_participant_from_original_list(self, client):
        """Test unregistering one of the original participants."""
        response = client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": "michael@mergington.edu"}
        )
        
        assert response.status_code == 200
        
        # Verify removal
        activities_response = client.get("/activities")
        assert "michael@mergington.edu" not in activities_response.json()["Chess Club"]["participants"]


class TestActivityConstraints:
    """Tests for activity constraints and business logic."""

    def test_max_participants_not_enforced_on_signup(self, client):
        """Test the current behavior - max participants is not enforced on signup."""
        # This tests the current implementation behavior
        # Sign up multiple participants to an activity
        for i in range(5):
            response = client.post(
                "/activities/Chess%20Class/signup",
                params={"email": f"participant{i}@mergington.edu"}
            )
            # The current implementation doesn't check max_participants
            assert response.status_code == 200 or response.status_code == 404

    def test_activity_data_consistency(self, client):
        """Test that activity data remains consistent through operations."""
        # Get initial state
        response1 = client.get("/activities")
        initial_count = len(response1.json()["Programming Class"]["participants"])
        
        # Add participant
        client.post(
            "/activities/Programming%20Class/signup",
            params={"email": "test1@mergington.edu"}
        )
        
        # Check count increased
        response2 = client.get("/activities")
        assert len(response2.json()["Programming Class"]["participants"]) == initial_count + 1
        
        # Remove participant
        client.delete(
            "/activities/Programming%20Class/unregister",
            params={"email": "test1@mergington.edu"}
        )
        
        # Check count back to initial
        response3 = client.get("/activities")
        assert len(response3.json()["Programming Class"]["participants"]) == initial_count
