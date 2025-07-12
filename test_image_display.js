#!/usr/bin/env node
/**
 * Test script to verify image_url field is being fetched from API
 */

const fetch = require('node-fetch');

async function testImageDisplay() {
  try {
    console.log('🧪 Testing image display functionality...');
    
    // Test the API endpoint
    const response = await fetch('http://localhost:3000/api/products');
    const data = await response.json();
    
    if (data.products && data.products.length > 0) {
      console.log(`✅ Found ${data.products.length} products`);
      
      // Check if products have image_url
      const productsWithImages = data.products.filter(p => p.image_url);
      const productsWithoutImages = data.products.filter(p => !p.image_url);
      
      console.log(`📸 Products with images: ${productsWithImages.length}`);
      console.log(`❌ Products without images: ${productsWithoutImages.length}`);
      
      // Show some examples
      if (productsWithImages.length > 0) {
        console.log('\n📋 Sample products with images:');
        productsWithImages.slice(0, 3).forEach(product => {
          console.log(`  - ${product.name}: ${product.image_url}`);
        });
      }
      
      if (productsWithoutImages.length > 0) {
        console.log('\n📋 Sample products without images:');
        productsWithoutImages.slice(0, 3).forEach(product => {
          console.log(`  - ${product.name}: No image`);
        });
      }
      
    } else {
      console.log('❌ No products found in API response');
    }
    
  } catch (error) {
    console.error('❌ Error testing image display:', error.message);
  }
}

testImageDisplay(); 