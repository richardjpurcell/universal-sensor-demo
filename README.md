# Universal Sensor: Adaptive Wildfire Sensing Framework

This repository contains the codebase and simulation environment for the **Universal Sensor**, a software-defined, cognitive-inspired sensing architecture designed to operate in dynamic, uncertain environments such as wildfires.

## 🔍 Overview

The Universal Sensor implements an adaptive loop of **prediction, sensing, comparison, and control**, enabling each sensor to:
- Adjust sampling rates based on statistical entropy
- Transmit data based on KL-divergence surprise
- Reduce energy and bandwidth use while preserving critical wildfire event detection

The framework supports side-by-side evaluation of Universal vs. Typical (fixed-rate) sensors over wildfire simulations based on real data from the 2016 Fort McMurray event.