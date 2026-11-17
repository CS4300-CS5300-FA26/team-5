# Story 10 / issue #15. Friend activity itself is implemented separately in #18.
Feature: Friend requests
  Background:
    Given I am logged in

  Scenario: Send a request
    Given a valid username
    When I send a friend request
    Then the other player sees it as pending

  Scenario: Unknown username
    Given a username that does not exist
    When I send a friend request
    Then I see "No player with that username"
    And no friend request is sent

  Scenario: Accept
    Given a pending request
    When I accept it
    Then we both appear in each other's friends list

  Scenario: Decline
    Given a pending request
    When I decline it
    Then that player does not appear in my friends list

  Scenario: Remove a friend
    Given a friend
    When I remove them
    Then we disappear from each other's friends list
