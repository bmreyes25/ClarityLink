# Apple R15 and second-screen evidence

**APPLE DOCUMENTED:** WWDC19 “Advances in CarPlay Systems” states that before iOS 13 the iPhone provided one H.264 CarPlay stream; iOS 13 supports multiple H.264 streams for instrument-cluster content, including map and maneuver-card content in different cluster areas. It discusses ViewArea/SafeArea and states the second-screen vehicle-system capabilities require CarPlay Communication plug-in R15. [Apple WWDC19](https://developer.apple.com/videos/play/wwdc2019/252/)

**APPLE DOCUMENTED:** WWDC23 describes view areas as UI boundaries and safe areas as the guaranteed visible/interactable rectangle, extending vehicle layout and display integration concepts. [Apple WWDC23](https://developer.apple.com/videos/wwdc2023/10150/)

These documents establish Apple capability generations, not Honda's licensed plug-in revision or protocol fields. Honda's older receiver has a one-display `/info` builder and Type111 invalid dispatch; no evidence establishes R15 support. Modern `FeatureKey` tokens such as `altScreen` must not be assumed necessary for older `/info` negotiation.
