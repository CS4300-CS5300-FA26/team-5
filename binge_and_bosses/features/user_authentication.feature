# Story #8: User Authentication
# As a returning player, I want to log in and out, so that only I can change my lists.

Feature: Log in and log out

  Scenario: Correct credentials
    Given I have a registered account
    When I enter the correct username and password
    Then I land on my library

  Scenario: Log out
    Given I am logged in
    When I click "Logout"
    Then I am returned to the login page

  Scenario: Wrong username or password
    Given I am on the login page
    When I enter a username or password that does not match an account
    Then I see the error "Invalid username or password."
    And the message does not reveal whether the username is registered
