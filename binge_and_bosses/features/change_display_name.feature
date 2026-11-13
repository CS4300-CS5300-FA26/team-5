# Story 12: Profile Customization

Feature: Profile Customization
    Scenario: Change display name
        Given I am logged in
        When I save a new display name
        Then it shows on my profile.