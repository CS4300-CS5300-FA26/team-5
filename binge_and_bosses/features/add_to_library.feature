# Story 7: Add to Library
# As a player, I want to add a game to my library, so that I can track it alongside everything else I play.

@fake_rawg
Feature: Add to library

  Scenario: Add a new game
    Given I am logged in on a game page
    When I click "Add to library"
    Then the game appears in my library as "Not Started"

  Scenario: Game already in library
    Given the game is already in my library
    When I open its page
    Then the button reads "In library" and cannot add a duplicate

  Scenario: Not logged in
    Given I am not logged in
    When I click "Add to library"
    Then I am asked to log in and nothing is added