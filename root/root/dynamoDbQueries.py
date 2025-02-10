queries = {
    'createUserAction': """ mutation CreateUserActivity(
    $input: CreateUserActivityInput!
    $condition: ModelUserActivityConditionInput
  ) {
    createUserActivity(input: $input, condition: $condition) {
      id
      user_id
      action
      _version
      _deleted
      _lastChangedAt
      createdAt
      updatedAt
    }
  }""",
    'updateUserActivity': """ mutation UpdateUserActivity(
    $input: UpdateUserActivityInput!
    $condition: ModelUserActivityConditionInput
    ) {
        updateUserActivity(input: $input, condition: $condition) {
        id
    user_id
    action
    _version
    _deleted
    _lastChangedAt
    createdAt
    updatedAt
    }
    }""",
    'deleteUserActivity': """mutation DeleteUserActivity(
      $input: DeleteUserActivityInput!
      $condition: ModelUserActivityConditionInput
      ) {
      deleteUserActivity(input: $input, condition: $condition) {
      id
      user_id
      action
      _version
      _deleted
      _lastChangedAt
      createdAt
      updatedAt
      }
      }"""
}
