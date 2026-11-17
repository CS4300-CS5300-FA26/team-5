Feature: Landing page
  As a visitor, I want a home page that explains Binge & Bosses,
  so that I know what the app does and how to start.

  Scenario: Visitor learns what the app does
    Given I am not logged in
    When I visit the home page
    Then I see what Binge & Bosses is for
    And I see a "Sign up" link and a "Log in" link

  Scenario: Visitor starts signing up
    Given I am not logged in
    And I am on the home page
    When I follow "Sign up"
    Then I am on the sign-up page

  Scenario: Logged-in player continues where they left off
    Given I am logged in
    When I visit the home page
    Then I see links to my library and to search
    And I do not see a "Sign up" link

  Scenario: Logged-in player sees their own games
    Given I am logged in
    And my library has "Hades II" and "Balatro"
    When I visit the home page
    Then I see "Balatro" and "Hades II" under Recently added
