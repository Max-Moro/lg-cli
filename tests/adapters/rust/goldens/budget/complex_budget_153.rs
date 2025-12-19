








/// Module level long documentation that might be truncated under tight budgets.






/// PublicService provides public API operations.
pub struct PublicService {
    ,
}

impl PublicService {
    /// Creates a new service instance.
    pub fn new() -> Self 

    /// GetUser is a public API method that gets a user by ID.
    pub fn get_user(&self, id: i32) -> Option<&User> 

    /// normalize is a private helper — should not be visible with public_api_only.
    

    /// Process is a long method body to allow function body stripping.
    pub fn process(&mut self, list: Vec<User>) -> Result<Vec<User>> 
}

/// internalOnly is a private struct — should be filtered out in public_api_only.




/// PublicFunction is an exported function.
pub fn public_function(name: String) -> String
