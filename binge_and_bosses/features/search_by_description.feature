# Search by description (AI): describe the kind of game you want instead of typing its title

@fake_igdb
Feature: Search by description

  Scenario: Describe a game
    Given I describe "a monster-catching RPG on Game Boy"
    When results load
    Then I see games with matching titles and cover art
    And I see what the search looked for

  Scenario: The description can't be read
    Given I describe "a monster-catching RPG on Game Boy"
    And the description can't be read
    When results load
    Then I see "Could not load games. Try again."
