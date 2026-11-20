# Search results show every match, a page at a time

@fake_igdb
Feature: Page through search results
  As a player, I want to see every game that matches my search,
  so that I can find a game that isn't in the first few results.

  Background:
    Given IGDB has 30 games matching "Quest"
    And I search "Quest"

  Scenario: Ten results by default
    When results load
    Then I see results 1 to 10 of 30

  Scenario: Next page
    When results load
    And I follow "Next ›"
    Then I see results 11 to 20 of 30

  Scenario: Show more results per page
    When I choose to show 25 results per page
    Then I see results 1 to 25 of 30

  Scenario: Go to a typed page
    When results load
    And I go to page 3
    Then I see results 21 to 30 of 30
