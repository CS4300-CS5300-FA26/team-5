# Story 1: Changing Play Status (#12)
# As a player, I want to change a game's play status, so that my library shows what I'm playing, finished, or dropped.

@fake_igdb
Feature: Play status

  Scenario: Start playing
    Given a game in my library marked "Not Started"
    When I change its status to "Playing"
    Then my library shows it under "Playing"

  Scenario: Drop a game
    Given a game marked "Playing"
    When I mark it "Dropped"
    Then it leaves "Playing"
    And its rating and review are kept

  Scenario: Not logged in
    Given I am not logged in
    When I try to change a status
    Then I am asked to log in and nothing changes
