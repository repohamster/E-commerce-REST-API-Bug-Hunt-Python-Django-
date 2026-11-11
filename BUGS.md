# Known Bugs

The API includes six intentional defects. The regression tests describe the expected behavior.

- Login does not consistently reject an incorrect password.
- Product listing can return the wrong page of results.
- Updating a cart item can result in an unexpected quantity.
- An order can be placed even when the cart requests more stock than is available.
- The total recorded for an order can disagree with the value of its items.
- A protected endpoint can respond successfully without a login token.
