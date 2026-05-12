package com.carmonitor.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DirectionsCar
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                CarMonitorApp()
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CarMonitorApp() {
    var listings by remember { mutableStateOf(getSampleListings()) }
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = { 
                    Column {
                        Text("🚗 Car Monitor")
                        Text(
                            "${listings.size} annonces",
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                },
                actions = {
                    IconButton(onClick = { 
                        listings = getSampleListings()
                    }) {
                        Icon(Icons.Default.Refresh, "Actualiser")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                )
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            items(listings) { listing ->
                CarListingCard(listing)
            }
        }
    }
}

@Composable
fun CarListingCard(listing: CarListing) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    Icons.Default.DirectionsCar,
                    contentDescription = null,
                    modifier = Modifier.size(40.dp),
                    tint = MaterialTheme.colorScheme.primary
                )
                
                Surface(
                    color = if (listing.isNew) Color(0xFF4CAF50) else Color.Gray,
                    shape = MaterialTheme.shapes.small
                ) {
                    Text(
                        text = if (listing.isNew) "NOUVEAU" else listing.source.uppercase(),
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = Color.White
                    )
                }
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Text(
                text = listing.title,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            
            Spacer(modifier = Modifier.height(4.dp))
            
            Text(
                text = "${listing.price} TND",
                style = MaterialTheme.typography.titleLarge,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Bold
            )
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "📍 ${listing.location}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color.Gray
                )
                
                Text(
                    text = "📅 ${listing.year}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color.Gray
                )
            }
        }
    }
}

data class CarListing(
    val title: String,
    val price: String,
    val location: String,
    val year: Int,
    val source: String,
    val isNew: Boolean
)

fun getSampleListings() = listOf(
    CarListing("Renault Clio 4", "28 000", "Tunis", 2018, "tayara", true),
    CarListing("Peugeot 208", "32 000", "Ariana", 2019, "9annas", true),
    CarListing("Mercedes C200", "85 000", "Sousse", 2017, "tayara", false),
    CarListing("BMW Serie 3", "75 000", "Sfax", 2016, "tunisie-annonce", false),
    CarListing("Volkswagen Golf 7", "42 000", "Ben Arous", 2018, "tayara", true),
    CarListing("Toyota Corolla", "38 000", "Nabeul", 2017, "9annas", false),
    CarListing("Hyundai i20", "25 000", "Bizerte", 2016, "tayara", false),
    CarListing("Fiat 500", "22 000", "Monastir", 2015, "9annas", true)
)
