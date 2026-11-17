@fake_igdb
Feature: Players' average rating
  As a player, I want to see how our players rated a game,
  so that I know what people here think of it before I play.

  Scenario: Several players rated the game
    Given players rated the game 3, 4 and 5 stars
    And another player has the game but did not rate it
    When I open its page
    Then the players' score reads "4.0 / 5 · 3 ratings"

  Scenario: Nobody has rated the game yet
    Given a game in my library
    When I open its page
    Then there is no players' score
