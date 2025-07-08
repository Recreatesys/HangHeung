# POS Cost Centre Configuration Module

## Overview
The POS Cost Centre Configuration module allows users to manage cost centres within the Point of Sale (POS) system. This module provides a structured way to define and select cost centres for transactions, enhancing financial tracking and reporting.

## Features
- **Cost Centre Management**: Users can create, read, update, and delete cost centre records.
- **Integration with POS**: The module integrates seamlessly with the POS system, allowing users to select cost centres during transactions.
- **Custom Field**: A custom field for selecting the cost centre is included in the POS configuration.

## Installation
1. **Download the Module**: Clone or download the module from the repository.
2. **Place in Addons Directory**: Move the `pos_cost_centre_config` directory to your Odoo addons directory.
3. **Update App List**: Go to the Odoo backend, navigate to Apps, and click on "Update Apps List".
4. **Install the Module**: Search for "POS Cost Centre Configuration" and click on the install button.

## Usage
- After installation, navigate to the POS settings to configure cost centres.
- Users can add new cost centres through the Cost Centre management interface.
- When configuring POS, users can select the appropriate cost centre for each transaction.

## Models
- **PosCostCentre**: Represents the main model for POS Cost Centre configuration.
- **CostCentre**: Represents the model for managing cost centre records.

## Views
- Custom views are provided for both the `PosCostCentre` and `CostCentre` models, allowing for easy management and selection of cost centres.

## Security
Access rights are defined to ensure that only authorized users can manage cost centres and POS configurations.

## Support
For any issues or feature requests, please contact the module maintainer or raise an issue in the repository.