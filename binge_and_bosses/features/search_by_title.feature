# Story #9: Search by Game Title

@fake_rawg
Feature: Search by title

  Scenario: Matching titles
    Given I search "Pokemon"
    When results load
    Then I see games with matching titles and cover art

  Scenario: No matches
    Given I search a string that matches no game title
    When results load
    Then I see "No games found"
