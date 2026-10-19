# Story #7: User Registration
# As a new player, I want to create an account with my email and a password,
# so that my backlog is saved and I can reach it from any device.

Feature: User registration

  Scenario: Successful sign-up
    Given I am on the sign-up page
    When I submit a valid email and password
    Then I am logged in and see my empty library

  # Emails aren't unique yet, so a second account is created. Fixed in #62.
  @wip
  Scenario: Email already registered
    Given an account already exists for an email
    When I sign up with that email again
    Then no new account is created
    And I see "Unable to create an account with those details. Try logging in or resetting your password."
    And the message does not reveal whether the email is registered

  Scenario Outline: Invalid email or weak password
    Given I am on the sign-up page
    When I submit an invalid email format or a password shorter than 8 characters
      | email   | password   |
      | <email> | <password> |
    Then no account is created
    And I see an error next to the "<field>" field

    Examples:
      | email            | password      | field     |
      | not-an-email     | Gr8Backlog!42 | email     |
      | new@example.com  | Sh0rt!        | password2 |
