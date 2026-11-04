# Story 8: Rate a Game (#13)
# As a player, I want to rate a game from 1 to 5, so that I remember how much I liked it.

@fake_rawg
Feature: Ratings

  Scenario: Rate a game
    Given a game in my library
    When I select 4 stars
    Then my library shows 4 stars on that game

  Scenario: Change a rating
    Given a game I have already rated
    When I pick a new rating
    Then the old rating is replaced
