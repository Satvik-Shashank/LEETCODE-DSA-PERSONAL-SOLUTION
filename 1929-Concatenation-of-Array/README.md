# 1929. Concatenation of Array

**Difficulty:** Easy

---

## Problem Summary

Given an integer array nums of length n, you want to create an array ans of length 2n where ans[i] == nums[i] and ans[i + n] == nums[i] for 0 <= i < n (0-indexed).

Specifically, ans is the concatenation of two nums arrays.

Return the array ans.

 
Example 1:

Input: nums = [1,2,1]
Output: [1,2,1,1,2,1]
Explanation: The array ans is formed as follows:
- ans = [nums[0],nums[1],nums[2],nums[0],nums[1],nums[2]]
- ans = [1,2,1,1,2,1]

Example 2:

Input: nums = [1,3,2,1]
Output: ...

---

## Approach

### Most Efficient Approach

**Pattern: Array Concat**

1. Create a new result array of the required size.
2. Copy elements from the source array into the result.
3. Repeat or mirror the copy as needed to fill the result.
4. Return the constructed array.

### My Approach

1. Return the final result.

---

## Complexity Analysis

| Metric | Value |
|--------|-------|
| Time   | O(1) |
| Space  | O(1) |

Constant-time operations with no loops. No significant extra space is used.

---

## Code

```py
class Solution:
    def getConcatenation(self, nums: List[int]) -> List[int]:
        return nums + nums
```
