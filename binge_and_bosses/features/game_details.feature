# Story #10: Game Details Page

Feature: Game details

  Scenario: Open a game from search results
    Given search results are on the screen
    When I click a game
    Then I see its cover, genre(s), platform(s), and description

  Scenario: Details fail to load
    Given search results are on the screen
    And the game database is unavailable
    When I click a game
    Then I see "Could not load game details. Try again."
    And I stay on the search results

  Scenario: Missing fields
    Given a game has no description or cover
    When I open its details page
    Then I see "No description available"
    And I see a default cover
