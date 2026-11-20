# Search results say what each game is and what it's about

@fake_igdb
Feature: Search result details
  As a player, I want each search result to tell me about the game,
  so that I can pick the right one without opening every result.

  Scenario: A result shows the game's facts and summary
    Given I search "Pokemon"
    When results load
    Then each result shows its year, genres, score, summary and platforms
