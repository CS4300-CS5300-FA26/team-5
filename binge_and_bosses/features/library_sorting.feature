Feature: Sort my library
  As a player, I want to sort my library,
  so that I can find a game quickly.

  Background:
    Given I am logged in
    And I added these games to my library, in this order:
      | title    | rating |
      | Celeste  | 3      |
      | Balatro  |        |
      | Hades II | 5      |
    And I am on the library page

  Scenario: Newest first by default
    Then my library lists "Hades II, Balatro, Celeste"

  Scenario: Sort by title
    When I follow "Title"
    Then my library lists "Balatro, Celeste, Hades II"

  Scenario: Sort by rating, with unrated games last
    When I follow "Rating"
    Then my library lists "Hades II, Celeste, Balatro"
