# Story 9: Reviews (#14)
# As a player, I want to write and edit reviews and read other players' reviews, so that I remember why I liked a game and can decide what to play.

@fake_rawg
Feature: Reviews

  Scenario: Save a review
    Given a game in my library
    When I save a review
    Then it appears on that game's page under my username

  Scenario: Edit a review
    Given I have a review on a game
    When I edit and save it
    Then the new text replaces the old text
    And the review shows an "edited" label

  Scenario: Read other reviews
    Given other users reviewed a game
    When I open its page
    Then I see all their ratings and reviews
